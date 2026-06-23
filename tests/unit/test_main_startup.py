from __future__ import annotations

from unittest.mock import patch

import main as app_main


def test_main_shows_clear_error_when_initial_admin_credentials_are_missing(
    monkeypatch,
) -> None:
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    with (
        patch.object(app_main, "load_dotenv", return_value=False),
        patch.object(
            app_main,
            "initialize_storage",
            side_effect=ValueError(
                "ADMIN_USERNAME and ADMIN_PASSWORD must be set in the "
                "environment (or .env) when no admin account exists."
            ),
        ),
        patch.object(app_main.QMessageBox, "critical") as mock_critical,
    ):
        exit_code = app_main.main([])

    assert exit_code == 1
    message = mock_critical.call_args.args[2]
    assert "Initial admin credentials are required" in message
    assert "ADMIN_USERNAME and ADMIN_PASSWORD" in message
    assert "database migration error" not in message
