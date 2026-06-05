"""
Contract tests for CachingFaceReferenceRepository.

The wrapper exists to make cache invalidation *enforced* (not by convention).
These tests pin that invariant: every public write method must invalidate the
cache, and a read after a write must return fresh data.

We use a stub (not a mock) for the inner repository to keep the test readable
on failure — a stub records call counts, a mock would require setup gymnastics
for spec/return values.
"""

from __future__ import annotations

import pytest

from attendance_system.repositories.caching_face_reference_repository import (
    CachingFaceReferenceRepository,
)
from attendance_system.repositories.face_reference_repository import POSE_LABELS


# ---------------------------------------------------------------------------
# Stub inner repository
# ---------------------------------------------------------------------------


class StubFaceReferenceRepository:
    """In-memory fake that records every call.

    Implements the same surface the wrapper delegates to. Each method records
    its call and returns a deterministic value the test can assert on.
    """

    def __init__(self, database=None) -> None:
        if database is None:
            self.database = self  # __getattr__ test expects this
        else:
            self.database = database
        self.calls: list[tuple[str, tuple, dict]] = []
        # Mutable state the stub "stores" so reads return what writes put in.
        self._refs: list[dict] = []
        # Simulates whether save_enrollment also updates the users table
        # (the wrapper doesn't care; this is purely for caller-side tests).
        # Provide a config path so the wrapper's _cache_key() works.
        self.config = type("Config", (), {"path": ":memory:"})()

    def _record(self, name: str, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    def get_all(self):
        self._record("get_all")
        return list(self._refs)

    def get_by_user_id(self, user_id):
        self._record("get_by_user_id", user_id)
        return [r for r in self._refs if r.get("user_id") == user_id]

    def get_by_user_id_and_pose(self, user_id, pose_label):
        self._record("get_by_user_id_and_pose", user_id, pose_label)
        for r in self._refs:
            if r.get("user_id") == user_id and r.get("pose_label") == pose_label:
                return r
        return None

    def upsert(self, user_id, embedding, model_name, vector_length, pose_label="center"):
        self._record("upsert", user_id, embedding, model_name, vector_length, pose_label)
        # Remove any existing for the same (user_id, pose_label)
        self._refs = [
            r for r in self._refs
            if not (r.get("user_id") == user_id and r.get("pose_label") == pose_label)
        ]
        self._refs.append({
            "user_id": user_id,
            "embedding": embedding,
            "model_name": model_name,
            "vector_length": vector_length,
            "pose_label": pose_label,
        })
        return len(self._refs)

    def replace_all(self, user_id, pose_embeddings, model_name, vector_length):
        self._record("replace_all", user_id, pose_embeddings, model_name, vector_length)
        self._refs = [r for r in self._refs if r.get("user_id") != user_id]
        for pose_label in POSE_LABELS:
            self._refs.append({
                "user_id": user_id,
                "embedding": pose_embeddings[pose_label],
                "model_name": model_name,
                "vector_length": vector_length,
                "pose_label": pose_label,
            })

    def delete_by_user_id(self, user_id):
        self._record("delete_by_user_id", user_id)
        self._refs = [r for r in self._refs if r.get("user_id") != user_id]

    def save_enrollment(self, user_id, pose_embeddings, model_name, vector_length):
        self._record("save_enrollment", user_id, pose_embeddings, model_name, vector_length)
        self.replace_all(user_id, pose_embeddings, model_name, vector_length)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_inner():
    return StubFaceReferenceRepository()


@pytest.fixture
def wrapper(stub_inner):
    return CachingFaceReferenceRepository(stub_inner)


# ---------------------------------------------------------------------------
# 1. The contract invariant: every write invalidates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("write_method,write_kwargs", [
    ("upsert", {"embedding": b"\x00", "model_name": "m", "vector_length": 1, "pose_label": "center"}),
    ("replace_all", {"pose_embeddings": {p: b"\x00" for p in POSE_LABELS}, "model_name": "m", "vector_length": 1}),
    ("delete_by_user_id", {}),
    ("save_enrollment", {"pose_embeddings": {p: b"\x00" for p in POSE_LABELS}, "model_name": "m", "vector_length": 1}),
])
def test_every_write_invalidates_cache(wrapper, stub_inner, write_method, write_kwargs):
    """The core invariant: after any public write, the next read hits the inner repo."""
    # Populate cache
    wrapper.get_all()
    get_all_before = sum(1 for c in stub_inner.calls if c[0] == "get_all")
    assert get_all_before == 1  # cache populated

    # Invoke the write method
    method = getattr(wrapper, write_method)
    if write_method == "delete_by_user_id":
        method(42)
    else:
        method(42, **write_kwargs)

    # Next read MUST hit the inner again (cache was invalidated)
    wrapper.get_all()
    get_all_after = sum(1 for c in stub_inner.calls if c[0] == "get_all")
    assert get_all_after == get_all_before + 1, (
        f"Cache was not invalidated by {write_method}! "
        f"Inner get_all calls: {get_all_before} -> {get_all_after}"
    )


# ---------------------------------------------------------------------------
# 2. Read caching behaviour
# ---------------------------------------------------------------------------


def test_first_get_all_populates_cache(wrapper, stub_inner):
    assert len(stub_inner.calls) == 0
    wrapper.get_all()
    assert len(stub_inner.calls) == 1


def test_second_get_all_returns_cached(wrapper, stub_inner):
    wrapper.get_all()
    wrapper.get_all()
    wrapper.get_all()
    # Only the first call hit the inner
    assert len(stub_inner.calls) == 1


def test_read_after_write_returns_fresh_data(wrapper, stub_inner):
    """Write via wrapper invalidates cache so the next read returns fresh data."""
    # Populate cache — initial empty state
    assert wrapper.get_all() == []

    # Write via the wrapper (this both writes AND invalidates cache)
    wrapper.upsert(1, b"x", "m", 1, "center")

    # Read again — cache was invalidated, must re-read from inner
    result = wrapper.get_all()
    assert len(result) == 1
    assert result[0]["user_id"] == 1


# ---------------------------------------------------------------------------
# 3. Public invalidation hook
# ---------------------------------------------------------------------------


def test_invalidate_public_method_works(wrapper, stub_inner):
    wrapper.get_all()  # populate
    assert len(stub_inner.calls) == 1
    wrapper.invalidate()
    wrapper.get_all()  # must re-read
    assert len(stub_inner.calls) == 2


def test_invalidate_with_user_id_is_accepted(wrapper, stub_inner):
    """user_id is currently ignored; the public method must accept it for future use."""
    wrapper.get_all()
    wrapper.invalidate(user_id=42)
    # No assertion needed beyond "doesn't raise"
    wrapper.get_all()


# ---------------------------------------------------------------------------
# 4. Pass-through delegation for non-cached reads
# ---------------------------------------------------------------------------


def test_get_by_user_id_delegates_to_inner(wrapper, stub_inner):
    wrapper.get_by_user_id(7)
    assert ("get_by_user_id", (7,), {}) in stub_inner.calls


def test_get_by_user_id_and_pose_delegates_to_inner(wrapper, stub_inner):
    wrapper.get_by_user_id_and_pose(7, "center")
    assert ("get_by_user_id_and_pose", (7, "center"), {}) in stub_inner.calls


# ---------------------------------------------------------------------------
# 5. __getattr__ pass-through (so callers can reach .database etc.)
# ---------------------------------------------------------------------------


def test_getattr_passes_through_unknown_attributes(wrapper, stub_inner):
    # .database is not spelled out on the wrapper; it should fall through to inner
    assert wrapper.database is stub_inner


def test_getattr_raises_attribute_error_for_unknown_attribute(wrapper):
    with pytest.raises(AttributeError):
        wrapper.this_method_does_not_exist


# ---------------------------------------------------------------------------
# 6. Exception path: writes do NOT invalidate on failure
# ---------------------------------------------------------------------------


class FailingInner(StubFaceReferenceRepository):
    """Stub whose `replace_all` always raises. Used to verify that failed writes
    do NOT invalidate the cache (the cache is still correct)."""

    def replace_all(self, *args, **kwargs):
        self._record("replace_all", *args, **kwargs)
        raise RuntimeError("simulated DB failure")


def test_failed_write_does_not_invalidate_cache():
    failing = FailingInner()
    wrapper = CachingFaceReferenceRepository(failing)

    # Populate cache
    wrapper.get_all()
    assert len(failing.calls) == 1

    # Attempt a write that will fail
    with pytest.raises(RuntimeError, match="simulated DB failure"):
        wrapper.replace_all(
            42,
            {p: b"\x00" for p in POSE_LABELS},
            "m",
            1,
        )

    # Cache is still valid (NOT invalidated because the write failed)
    wrapper.get_all()
    # Only one inner.get_all() call — the second wrapper.get_all() was served from cache
    assert sum(1 for c in failing.calls if c[0] == "get_all") == 1
