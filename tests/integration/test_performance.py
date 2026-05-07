from __future__ import annotations

from time import perf_counter

from attendance_system.repositories.user_repository import UserRepository


def test_basic_crud_operations_complete_quickly(database) -> None:
    users = UserRepository(database)

    start = perf_counter()
    user_id = users.create("SV009", "Nguyen Van I")
    users.get_by_id(user_id)
    duration = perf_counter() - start

    assert duration < 1.0
