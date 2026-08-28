import json

import pytest

from blackfish.pipelines.payload import PayloadError, PayloadStore


class TestInlinePayloads:
    def test_small_values_stay_in_the_reference(self, tmp_path):
        store = PayloadStore(tmp_path)
        ref = store.put({"path": "/data/a.wav"})
        assert ref.startswith("inline:")
        assert store.get(ref) == {"path": "/data/a.wav"}

    def test_nothing_is_written_to_disk_for_inline_values(self, tmp_path):
        store = PayloadStore(tmp_path)
        store.put("small")
        assert not list(tmp_path.rglob("*.json"))

    @pytest.mark.parametrize(
        "value", [None, 0, "", [], {}, [1, "two", {"three": 4.0}], True]
    )
    def test_round_trips_json_values(self, tmp_path, value):
        store = PayloadStore(tmp_path)
        assert store.get(store.put(value)) == value


class TestSpilledPayloads:
    def test_large_values_go_to_disk(self, tmp_path):
        store = PayloadStore(tmp_path, inline_max_bytes=16)
        ref = store.put({"text": "x" * 100})
        assert ref.startswith("file:")
        assert store.get(ref) == {"text": "x" * 100}

    def test_identical_values_share_one_file(self, tmp_path):
        """Content addressing is what makes a retried write a no-op."""
        store = PayloadStore(tmp_path, inline_max_bytes=0)
        first = store.put({"a": 1})
        second = store.put({"a": 1})
        assert first == second
        assert len(list(tmp_path.rglob("*.json"))) == 1

    def test_key_order_does_not_change_the_reference(self, tmp_path):
        store = PayloadStore(tmp_path, inline_max_bytes=0)
        assert store.put({"a": 1, "b": 2}) == store.put({"b": 2, "a": 1})

    def test_different_values_get_different_files(self, tmp_path):
        store = PayloadStore(tmp_path, inline_max_bytes=0)
        assert store.put({"a": 1}) != store.put({"a": 2})

    def test_no_partial_files_are_left_behind(self, tmp_path):
        store = PayloadStore(tmp_path, inline_max_bytes=0)
        store.put({"a": 1})
        assert not [p for p in tmp_path.rglob(".tmp-*")]


class TestErrors:
    def test_rejects_values_json_cannot_encode(self, tmp_path):
        store = PayloadStore(tmp_path)
        with pytest.raises(PayloadError, match="not JSON-serializable"):
            store.put({"tensor": object()})

    def test_error_points_at_the_shared_filesystem_workaround(self, tmp_path):
        store = PayloadStore(tmp_path)
        with pytest.raises(PayloadError, match="pass the path instead"):
            store.put(object())

    def test_missing_spilled_file_is_reported_clearly(self, tmp_path):
        store = PayloadStore(tmp_path, inline_max_bytes=0)
        ref = store.put({"a": 1})
        for path in tmp_path.rglob("*.json"):
            path.unlink()
        with pytest.raises(PayloadError, match="filesystem this node can see"):
            store.get(ref)

    def test_rejects_an_unrecognized_reference(self, tmp_path):
        store = PayloadStore(tmp_path)
        with pytest.raises(PayloadError, match="Unrecognized payload reference"):
            store.get("s3://bucket/key")

    def test_rejects_a_corrupt_spilled_file(self, tmp_path):
        store = PayloadStore(tmp_path, inline_max_bytes=0)
        ref = store.put({"a": 1})
        path = next(tmp_path.rglob("*.json"))
        path.write_text("{not json")
        with pytest.raises(PayloadError, match="Malformed spilled payload"):
            store.get(ref)

    def test_rejects_a_negative_threshold(self, tmp_path):
        with pytest.raises(ValueError, match="inline_max_bytes"):
            PayloadStore(tmp_path, inline_max_bytes=-1)


def test_a_reference_survives_a_new_store_over_the_same_directory(tmp_path):
    """Workers construct their own store; the reference must still resolve."""
    written = PayloadStore(tmp_path, inline_max_bytes=0).put({"a": 1})
    assert PayloadStore(tmp_path, inline_max_bytes=0).get(written) == {"a": 1}


def test_spilled_files_hold_exactly_the_encoded_value(tmp_path):
    store = PayloadStore(tmp_path, inline_max_bytes=0)
    store.put({"a": 1})
    path = next(tmp_path.rglob("*.json"))
    assert json.loads(path.read_text()) == {"a": 1}
