import importlib
from typing import Any

import allure
from infra_core.aws.s3 import S3Client
from integration_test_utils import read_s3_json
from pytest import MonkeyPatch


def _load_handler(monkeypatch: MonkeyPatch, s3_client: Any, bucket: str) -> Any:
    monkeypatch.setenv("S3_BUCKET", bucket)

    handler: Any = importlib.import_module("sample_sqs_handler_app.handler")
    handler = importlib.reload(handler)
    handler._s3 = S3Client(client=s3_client)
    return handler


@allure.feature("SQS handler")
@allure.story("Save SQS records to S3")
def test_lambda_handler_saves_sqs_records_to_s3(
    monkeypatch: MonkeyPatch,
    s3_client: Any,
    integration_bucket: str,
) -> None:
    handler = _load_handler(monkeypatch, s3_client, integration_bucket)

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


@allure.feature("SQS handler")
@allure.story("Ignore invalid SQS records")
def test_lambda_handler_ignores_non_dict_records(
    monkeypatch: MonkeyPatch,
    s3_client: Any,
    integration_bucket: str,
) -> None:
    handler = _load_handler(monkeypatch, s3_client, integration_bucket)

    result = handler.lambda_handler(
        {
            "Records": [
                "not-a-record",
                None,
                {
                    "messageId": "message-json-002",
                    "eventSource": "aws:sqs",
                    "body": '{"order_id": "order-002", "amount": 3400}',
                },
            ]
        },
        None,
    )

    assert result == {
        "ok": True,
        "record_count": 1,
        "saved_keys": ["sqs-messages/message-json-002.json"],
    }

    json_payload = read_s3_json(
        s3_client,
        integration_bucket,
        "sqs-messages/message-json-002.json",
    )
    assert json_payload == {
        "message_id": "message-json-002",
        "event_source": "aws:sqs",
        "body": {"order_id": "order-002", "amount": 3400},
    }


@allure.feature("SQS handler")
@allure.story("Dashboard failure demo")
def test_lambda_handler_failure_demo_shows_allure_details(
    monkeypatch: MonkeyPatch,
    s3_client: Any,
    integration_bucket: str,
) -> None:
    handler = _load_handler(monkeypatch, s3_client, integration_bucket)

    result = handler.lambda_handler(
        {
            "Records": [
                {
                    "messageId": "message-failure-demo",
                    "eventSource": "aws:sqs",
                    "body": '{"order_id": "order-failure-demo", "amount": 9999}',
                },
            ]
        },
        None,
    )

    assert result["record_count"] == 2
