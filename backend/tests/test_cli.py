from __future__ import annotations

from productflow_backend import cli


def test_bootstrap_admin_prints_sensitive_cookie_to_stderr(monkeypatch, capsys) -> None:
    def fake_bootstrap_admin_session(
        *,
        new_api_user_id: str,
        new_api_username: str,
        ttl_hours: int,
    ) -> tuple[str, str]:
        assert new_api_user_id == "user-1"
        assert new_api_username == "alice"
        assert ttl_hours == 24
        return "session-1", "signed-cookie-value"

    monkeypatch.setattr(cli, "bootstrap_admin_session", fake_bootstrap_admin_session)

    exit_code = cli.main(
        [
            "bootstrap-admin",
            "--new-api-user-id",
            "user-1",
            "--new-api-username",
            "alice",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "session_id=session-1" in captured.out
    assert "cookie_name=session" in captured.out
    assert "signed-cookie-value" not in captured.out
    assert "cookie_value=signed-cookie-value" in captured.err
    assert "cookie_value is equivalent to an admin login secret" in captured.err
