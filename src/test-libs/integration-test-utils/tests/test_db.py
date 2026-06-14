import pytest

from integration_test_utils.db import reset_postgres_tables


def test_reset_postgres_tables_rejects_non_test_database() -> None:
    error_message = "Refusing to reset non-test database"
    with pytest.raises(RuntimeError, match=error_message):
        reset_postgres_tables(
            "postgresql://app:app@localhost:5432/app",
            ["processed_events"],
        )
