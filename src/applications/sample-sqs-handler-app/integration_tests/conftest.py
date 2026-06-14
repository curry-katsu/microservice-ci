from collections.abc import Iterator
from typing import Any

import pytest
from integration_test_utils import create_aws_client, delete_s3_prefix, ensure_s3_bucket


@pytest.fixture(scope="session")
def integration_bucket() -> str:
    return "sample-sqs-handler-app-integration-test"


@pytest.fixture(scope="session")
def s3_client() -> Any:
    return create_aws_client("s3")


@pytest.fixture(autouse=True)
def reset_s3_bucket(s3_client: Any, integration_bucket: str) -> Iterator[None]:
    ensure_s3_bucket(s3_client, integration_bucket)
    delete_s3_prefix(s3_client, integration_bucket, "sqs-messages/")
    yield
    delete_s3_prefix(s3_client, integration_bucket, "sqs-messages/")
