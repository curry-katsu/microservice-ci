from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import sql


def reset_postgres_tables(
    database_url: str,
    tables: list[str],
    *,
    seed_paths: list[Path] | None = None,
    required_database_suffix: str = "_test",
) -> None:
    _assert_test_database(database_url, required_database_suffix)
    if not tables:
        raise ValueError("tables must not be empty")

    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            identifiers = [sql.Identifier(table) for table in tables]
            cursor.execute(
                sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                    sql.SQL(", ").join(identifiers)
                )
            )

            for seed_path in seed_paths or []:
                cursor.execute(seed_path.read_text(encoding="utf-8"))


def _assert_test_database(database_url: str, required_suffix: str) -> None:
    database_name = urlparse(database_url).path.removeprefix("/")
    if not database_name.endswith(required_suffix):
        raise RuntimeError(
            f"Refusing to reset non-test database: {database_name!r}. "
            f"Expected suffix: {required_suffix!r}."
        )
