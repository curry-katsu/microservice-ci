import importlib
from typing import Any

from infra_core.aws.s3 import S3Client
from integration_test_utils import read_s3_json
from pytest import MonkeyPatch


def test_lambda_handler_saves_sqs_records_to_s3(
    monkeypatch: MonkeyPatch,
    s3_client: Any,
    integration_bucket: str,
) -> None:
    monkeypatch.setenv("S3_BUCKET", integration_bucket)

    handler: Any = importlib.import_module("sample_sqs_handler_app.handler")
    handler = importlib.reload(handler)
    handler._s3 = S3Client(client=s3_client)

    event = {
        "Records": [
            {
                "messageId": "message-json-001",
                "eventSource": "aws:sqs",
                "body": '{"order_id": "order-001", "amount": 1200}',
            },
            {
                "messageId": "message-text-001",
                "eventSource": "aws:sqs",
                "body": "plain text body",
            },
        ]
    }

    result = handler.lambda_handler(event, None)

    assert result == {
        "ok": True,
        "record_count": 2,
        "saved_keys": [
            "sqs-messages/message-json-001.json",
            "sqs-messages/message-text-001.json",
        ],
    }

    json_payload = read_s3_json(
        s3_client,
        integration_bucket,
        "sqs-messages/message-json-001.json",
    )
    assert json_payload == {
        "message_id": "message-json-001",
        "event_source": "aws:sqs",
        "body": {"order_id": "order-001", "amount": 1200},
    }

    text_payload = read_s3_json(
        s3_client,
        integration_bucket,
        "sqs-messages/message-text-001.json",
    )
    assert text_payload == {
        "message_id": "message-text-001",
        "event_source": "aws:sqs",
        "body": "plain text body",
    }
