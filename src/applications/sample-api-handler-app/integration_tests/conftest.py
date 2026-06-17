from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from integration_test_utils.aws import (
    create_aws_client,
    delete_s3_prefix,
    ensure_s3_bucket,
)
from integration_test_utils.db import reset_postgres_tables
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://app:app@localhost:5432/app_test"
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://app:app@localhost:5432/app_test"
AUDIT_BUCKET = "sample-api-handler-app-integration-test"


@pytest.fixture(scope="session")
def integration_bucket() -> str:
    return AUDIT_BUCKET


@pytest.fixture(scope="session")
def database_url() -> str:
    return DATABASE_URL


@pytest.fixture(scope="session")
def s3_client() -> Any:
    return create_aws_client("s3")


@pytest.fixture(scope="session", autouse=True)
def ensure_schema(database_url: str) -> None:
    schema_path = (
        Path(__file__).parents[4]
        / "local-env"
        / "database"
        / "init"
        / "001_create_tables.sql"
    )
    del database_url
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text(schema_path.read_text(encoding="utf-8")))
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_local_resources(
    database_url: str,
    integration_bucket: str,
    monkeypatch: pytest.MonkeyPatch,
    s3_client: Any,
) -> Iterator[None]:
    monkeypatch.setenv("API_AUTH_TOKEN", "integration-token")
    monkeypatch.setenv("AUDIT_BUCKET", integration_bucket)
    monkeypatch.setenv("DATABASE_URL", SQLALCHEMY_DATABASE_URL)

    reset_postgres_tables(database_url, ["api_orders"])
    ensure_s3_bucket(s3_client, integration_bucket)
    delete_s3_prefix(s3_client, integration_bucket, "api-orders/")
    yield
    reset_postgres_tables(database_url, ["api_orders"])
    delete_s3_prefix(s3_client, integration_bucket, "api-orders/")
