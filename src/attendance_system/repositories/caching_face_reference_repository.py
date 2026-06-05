"""
Caching wrapper around FaceReferenceRepository.

Intercepts reads (get_all cached in-memory) and writes (auto-invalidate
cache). Passes through all other attributes to the inner repository.
"""

from __future__ import annotations

from typing import Any

from .face_reference_repository import FaceReferenceRepository


class CachingFaceReferenceRepository:
    """
    Caching wrapper around FaceReferenceRepository.

    Cache invalidation is enforced by this class: every public write method
    (upsert, replace_all, delete_by_user_id, save_enrollment) invalidates
    the cache after the inner call returns. Forgetting to invalidate is
    impossible because the wrapper is the only code that touches the cache.

    Reads (get_all) consult the cache first; cache misses populate it.
    The cache is an in-memory dict keyed by the inner repo's database path,
    so different test databases (tmp_path) do not interfere.
    """

    def __init__(self, inner: FaceReferenceRepository) -> None:
        self._inner = inner
        # None = unpopulated; list[dict] = cached snapshot.
        # Keyed by database path so two repos on different DBs don't collide.
        self._cache: dict[str, list[dict[str, Any]]] = {}

    # ---- cache management ----

    def _cache_key(self) -> str:
        return str(self._inner.database.config.path)

    def _invalidate(self) -> None:
        """Clear the cache entry for this database path.

        Conservative full wipe (no per-user invalidation): the cache shape is
        a single list per DB path, so wiping the whole entry is the only safe
        option. Per-user invalidation would require restructuring the cache to
        a {user_id: [rows]} mapping, which the current hot path does not need.
        """
        self._cache.pop(self._cache_key(), None)

    def invalidate(self, user_id: int | None = None) -> None:
        """Public invalidation hook for tests and external triggers.

        ``user_id`` is accepted for forward-compatibility (per-user
        invalidation is a future option) but currently ignored — the cache
        is wiped wholesale on every call.
        """
        self._invalidate()

    # ---- reads (cached) ----

    def get_all(self) -> list[dict[str, Any]]:
        key = self._cache_key()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._inner.get_all()
        self._cache[key] = result
        return result

    def get_by_user_id(self, user_id: int) -> list[dict[str, Any]]:
        # Read methods other than get_all are not cached to avoid
        # cache-coherency complexity (per-user slices of a global cache).
        return self._inner.get_by_user_id(user_id)

    def get_by_user_id_and_pose(self, user_id: int, pose_label: str) -> Any:
        return self._inner.get_by_user_id_and_pose(user_id, pose_label)

    # ---- writes (always invalidate on success) ----

    def upsert(
        self,
        user_id: int,
        embedding: bytes,
        model_name: str,
        vector_length: int,
        pose_label: str = "center",
    ) -> int:
        result = self._inner.upsert(user_id, embedding, model_name, vector_length, pose_label)
        self._invalidate()
        return result

    def replace_all(
        self,
        user_id: int,
        pose_embeddings: dict[str, bytes],
        model_name: str,
        vector_length: int,
    ) -> None:
        self._inner.replace_all(user_id, pose_embeddings, model_name, vector_length)
        self._invalidate()

    def delete_by_user_id(self, user_id: int) -> None:
        self._inner.delete_by_user_id(user_id)
        self._invalidate()

    def save_enrollment(
        self,
        user_id: int,
        pose_embeddings: dict[str, bytes],
        model_name: str,
        vector_length: int,
    ) -> None:
        """Atomic enrollment (DELETE 5 rows + INSERT 5 rows + UPDATE users.face_registered).

        Delegates to inner.save_enrollment. Invalidates cache on success.
        """
        self._inner.save_enrollment(user_id, pose_embeddings, model_name, vector_length)
        self._invalidate()

    # ---- pass-through for everything else ----

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the inner repository.

        This keeps the wrapper's surface area minimal: only the methods that
        touch the cache (get_all and the 4 writes) are spelled out. Anything
        else (database, model_name, validation helpers, future methods) is
        reached via __getattr__.
        """
        return getattr(self._inner, name)
