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


class PayloadStore:
    """Encodes task payloads to references and back.

    Args:
        root: Directory for spilled payloads. On a cluster this must be on a
            filesystem every worker node can see, because a task leased by one
            node may have been produced by another.
        inline_max_bytes: Encoded payloads at or below this size stay in the
            queue row; larger ones are spilled to ``root``.
    """

    def __init__(
        self,
        root: str | os.PathLike[str],
        inline_max_bytes: int = DEFAULT_INLINE_MAX_BYTES,
    ) -> None:
        if inline_max_bytes < 0:
            raise ValueError("inline_max_bytes must be >= 0")
        self.root = Path(root)
        self.inline_max_bytes = inline_max_bytes

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
