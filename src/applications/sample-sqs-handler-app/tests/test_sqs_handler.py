import importlib
from typing import Any

import boto3
from infra_core.aws.s3 import S3Client
from moto import mock_aws
from pytest import MonkeyPatch


def test_lambda_handler_saves_sqs_record(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("S3_BUCKET", "unit-test-bucket")

    with mock_aws():
        s3_client: Any = boto3.client("s3", region_name="ap-northeast-1")
        s3_client.create_bucket(
            Bucket="unit-test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"},
        )

        handler: Any = importlib.import_module("sample_sqs_handler_app.handler")
        handler = importlib.reload(handler)
        handler._s3 = S3Client(client=s3_client)

        result = handler.lambda_handler(
            {
                "Records": [
                    {
                        "messageId": "message-001",
                        "eventSource": "aws:sqs",
                        "body": '{"value": 1}',
                    }
                ]
            },
            None,
        )

        assert result == {
            "ok": True,
            "record_count": 1,
            "saved_keys": ["sqs-messages/message-001.json"],
        }

        response = s3_client.get_object(
            Bucket="unit-test-bucket",
            Key="sqs-messages/message-001.json",
        )
        assert response["ContentType"] == "application/json"
        assert response["Body"].read().decode("utf-8") == (
            '{"message_id": "message-001", "event_source": "aws:sqs", '
            '"body": {"value": 1}}'
        )
