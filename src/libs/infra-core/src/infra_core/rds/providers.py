import os
from contextlib import contextmanager
from typing import Callable, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infra_core.rds.sessions import get_session_local


def _build_session_local_factory(database_url: str) -> Callable[[], Session]:
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


class RdsSessionProvider:
    def __init__(
        self,
        read_session_local_factory: Callable[[], Callable[[], Session]] | None = None,
        write_session_local_factory: Callable[[], Callable[[], Session]] | None = None,
    ) -> None:
        if read_session_local_factory is None and write_session_local_factory is None:
            (
                self._read_session_local_factory,
                self._write_session_local_factory,
            ) = self._build_default_factories()
        else:
            default_factory = get_session_local
            self._read_session_local_factory = (
                read_session_local_factory
                or write_session_local_factory
                or default_factory
            )
            self._write_session_local_factory = (
                write_session_local_factory
                or read_session_local_factory
                or default_factory
            )

        self._read_session_local: Callable[[], Session] | None = None
        self._write_session_local: Callable[[], Session] | None = None

    @staticmethod
    def _build_default_factories() -> tuple[
        Callable[[], Callable[[], Session]],
        Callable[[], Callable[[], Session]],
    ]:
        read_database_url = os.getenv("READ_DATABASE_URL")
        write_database_url = os.getenv("WRITE_DATABASE_URL")
        if not read_database_url and not write_database_url:
            return get_session_local, get_session_local

        read_url = read_database_url or write_database_url
        write_url = write_database_url or read_database_url
        if read_url is None or write_url is None:
            raise RuntimeError("RDS database URL configuration is missing.")

        if read_url == write_url:

            def factory() -> Callable[[], Session]:
                return _build_session_local_factory(read_url)

            return factory, factory

        def read_factory() -> Callable[[], Session]:
            return _build_session_local_factory(read_url)

        def write_factory() -> Callable[[], Session]:
            return _build_session_local_factory(write_url)

        return read_factory, write_factory

    def _get_read_session_local(self) -> Callable[[], Session]:
        if self._read_session_local is None:
            self._read_session_local = self._read_session_local_factory()
        return self._read_session_local

    def _get_write_session_local(self) -> Callable[[], Session]:
        if self._write_session_local is None:
            if (
                self._write_session_local_factory is self._read_session_local_factory
                and self._read_session_local is not None
            ):
                self._write_session_local = self._read_session_local
            else:
                self._write_session_local = self._write_session_local_factory()
        return self._write_session_local

    @contextmanager
    def read_session(self) -> Iterator[Session]:
        with self._get_read_session_local()() as session:
            yield session

    @contextmanager
    def write_transaction(self) -> Iterator[Session]:
        with self._get_write_session_local()() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    # Backward-compatible aliases.
    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.read_session() as session:
            yield session

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self.write_transaction() as session:
            yield session
