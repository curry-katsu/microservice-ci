from collections.abc import Callable
from typing import cast

import pytest
from sqlalchemy.orm import Session

from infra_core.rds.providers import RdsSessionProvider
from infra_core.rds.sessions import _build_database_url


class FakeSession:
    def __init__(self, fail_on_commit: bool = False) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.fail_on_commit = fail_on_commit

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def commit(self) -> None:
        if self.fail_on_commit:
            raise RuntimeError("commit failed")
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def _session_factory(session: FakeSession) -> Callable[[], Session]:
    def create_session() -> Session:
        return session  # type: ignore[return-value]

    return create_session


def _session_local_factory(session: FakeSession) -> Callable[[], Callable[[], Session]]:
    return lambda: _session_factory(session)


def test_build_database_url_uses_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db/app")

    assert _build_database_url() == "postgresql+psycopg://user:pass@db/app"


def test_build_database_url_from_db_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_HOST", "postgres")
    monkeypatch.setenv("DB_PORT", "15432")
    monkeypatch.setenv("DB_NAME", "service")

    assert (
        _build_database_url() == "postgresql+psycopg://user:pass@postgres:15432/service"
    )


def test_read_session_yields_session_without_commit() -> None:
    session = FakeSession()
    provider = RdsSessionProvider(
        read_session_local_factory=_session_local_factory(session)
    )

    with provider.read_session() as actual:
        assert cast(object, actual) is session

    assert session.closed is True
    assert session.committed is False
    assert session.rolled_back is False


def test_write_transaction_commits_on_success() -> None:
    session = FakeSession()
    provider = RdsSessionProvider(
        write_session_local_factory=_session_local_factory(session)
    )

    with provider.write_transaction() as actual:
        assert cast(object, actual) is session

    assert session.closed is True
    assert session.committed is True
    assert session.rolled_back is False


def test_write_transaction_rolls_back_on_error() -> None:
    session = FakeSession()
    provider = RdsSessionProvider(
        write_session_local_factory=_session_local_factory(session)
    )

    try:
        with provider.write_transaction():
            raise ValueError("failed")
    except ValueError:
        pass

    assert session.closed is True
    assert session.committed is False
    assert session.rolled_back is True
