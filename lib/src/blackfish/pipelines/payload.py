"""Task payloads: small values inline, large values spilled to shared storage.

A task queue is an index, not a data store. Putting a spectrogram or a batch of
embeddings *in* the queue makes every lease, retry and status query drag the
payload along with it. So a payload above ``inline_max_bytes`` is written once
to shared storage and the queue carries a reference.

Spilled payloads are content-addressed: the file name is the SHA-256 of the
encoded bytes. A retried task that recomputes the same output writes the same
path with the same contents, so at-least-once delivery cannot leave two
divergent copies behind, and a duplicate write is a no-op rather than a race.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

# Payloads at or below this size are carried inline in the queue row. 4 KiB is
# comfortably above a file path, a short prompt or a row of metadata -- the
# things a well-formed pipeline actually passes between jobs -- and well below
# the point where SQLite starts overflowing rows onto extra pages.
DEFAULT_INLINE_MAX_BYTES = 4096

_INLINE_PREFIX = "inline:"
_FILE_PREFIX = "file:"


class PayloadError(RuntimeError):
    """Raised when a payload cannot be encoded, stored, or read back."""


class PayloadTooLarge(PayloadError):
    """A payload needed spilling, and this store is not allowed to spill.

    Raised only when ``allow_spill=False``, which is how a process that cannot
    see the cluster's shared filesystem declares that fact. A coordinator
    running somewhere else -- a laptop, a container, the far side of an SSH
    tunnel -- can encode paths and small metadata perfectly well, and will
    silently write a file nobody can read the moment a payload gets large.
    Turning that into a loud error at submit time is much cheaper than finding
    it halfway through a run.
    """


class PayloadStore:
    """Encodes task payloads to references and back.

    Args:
        root: Directory for spilled payloads. On a cluster this must be on a
            filesystem every worker node can see, because a task leased by one
            node may have been produced by another. May be ``None`` only when
            ``allow_spill`` is ``False``.
        inline_max_bytes: Encoded payloads at or below this size stay in the
            queue row; larger ones are spilled to ``root``.
        allow_spill: Whether this store may write to ``root``. Set ``False`` in
            a process that cannot see the shared filesystem; oversized payloads
            then raise :class:`PayloadTooLarge` instead of being written
            somewhere no worker can read them.
    """

    def __init__(
        self,
        root: str | os.PathLike[str] | None = None,
        inline_max_bytes: int = DEFAULT_INLINE_MAX_BYTES,
        allow_spill: bool = True,
    ) -> None:
        if inline_max_bytes < 0:
            raise ValueError("inline_max_bytes must be >= 0")
        if allow_spill and root is None:
            raise ValueError(
                "A payload store that may spill needs a root directory."
                " Pass allow_spill=False for a process with no shared"
                " filesystem."
            )
        self.root = Path(root) if root is not None else None
        self.inline_max_bytes = inline_max_bytes
        self.allow_spill = allow_spill

    def put(self, value: Any) -> str:
        """Store ``value`` and return a reference to it.

        Args:
            value: Any JSON-serializable value. Anything larger than a modest
                blob -- audio, tensors, images -- belongs on the shared
                filesystem with its *path* passed here.

        Returns:
            A reference string, either ``inline:<json>`` or ``file:<sha256>``.

        Raises:
            PayloadError: If ``value`` is not JSON-serializable.
            PayloadTooLarge: If it needs spilling and this store may not spill.
        """
        try:
            encoded = json.dumps(value, sort_keys=True).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise PayloadError(
                f"Payload is not JSON-serializable ({exc}). Write large or"
                " non-JSON values to shared storage and pass the path instead."
            ) from exc

        if len(encoded) <= self.inline_max_bytes:
            return _INLINE_PREFIX + encoded.decode("utf-8")

        if not self.allow_spill:
            raise PayloadTooLarge(
                f"Payload is {len(encoded)} bytes, over the"
                f" {self.inline_max_bytes}-byte inline limit, and this store"
                " may not spill to disk. Write the value to storage the"
                " workers can see and pass its path instead."
            )

        digest = hashlib.sha256(encoded).hexdigest()
        path = self._path_for(digest)
        if not path.exists():
            write_atomic(path, encoded)
        return _FILE_PREFIX + digest

    def get(self, ref: str) -> Any:
        """Resolve a reference produced by :meth:`put`.

        Raises:
            PayloadError: If the reference is malformed or its backing file is
                missing.
        """
        if ref.startswith(_INLINE_PREFIX):
            raw = ref[len(_INLINE_PREFIX) :]
            try:
                return json.loads(raw)
            except ValueError as exc:
                raise PayloadError(f"Malformed inline payload: {exc}") from exc
        if ref.startswith(_FILE_PREFIX):
            digest = ref[len(_FILE_PREFIX) :]
            if self.root is None:
                raise PayloadError(
                    f"Payload {digest} lives on shared storage, but this store"
                    " has no root directory to read it from. A process that"
                    " resolves spilled payloads needs to see the filesystem"
                    " the workers write to."
                )
            path = self._path_for(digest)
            try:
                return json.loads(path.read_bytes())
            except FileNotFoundError as exc:
                raise PayloadError(
                    f"Spilled payload {digest} is missing from {self.root}."
                    " Is the payload store on a filesystem this node can see?"
                ) from exc
            except ValueError as exc:
                raise PayloadError(f"Malformed spilled payload {digest}") from exc
        raise PayloadError(f"Unrecognized payload reference: {ref!r}")

    def _path_for(self, digest: str) -> Path:
        # Two-character fan-out keeps directory listings usable on parallel
        # filesystems that dislike very wide directories.
        assert self.root is not None  # guarded by the callers
        return self.root / digest[:2] / f"{digest}.json"


def write_atomic(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` so readers never see a partial file.

    Exported because any job writing its own output -- a shard of embeddings, a
    transcript -- needs exactly this: a retried task must not leave a truncated
    file where a downstream job will later find one. Two workers retrying the
    same task write byte-identical content, so the rename is safe to lose:
    whichever lands last wins with the same bytes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
