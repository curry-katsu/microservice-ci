import importlib
import json
from typing import Any

from infra_core.aws.s3 import S3Client
from infra_core.rds.providers import RdsSessionProvider
from integration_test_utils import read_s3_json


def test_get_post_put_delete_order_api(
    database_url: str,
    integration_bucket: str,
    s3_client: Any,
) -> None:
    handler: Any = importlib.import_module("sample_api_handler_app.handler")
    handler = importlib.reload(handler)
    handler._rds = RdsSessionProvider()
    handler._s3 = S3Client(client=s3_client)

    created = _invoke(
        handler,
        "POST",
        "/orders",
        {
            "order_id": "order-001",
            "customer_id": "customer-001",
            "description": "Coffee beans",
            "amount": 2400,
        },
    )
    assert created["statusCode"] == 201
    assert json.loads(created["body"]) == {
        "amount": 2400,
        "customer_id": "customer-001",
        "description": "Coffee beans",
        "order_id": "order-001",
        "status": "pending",
    }

    fetched = _invoke(handler, "GET", "/orders/order-001")
    assert fetched["statusCode"] == 200
    assert json.loads(fetched["body"])["description"] == "Coffee beans"

    updated = _invoke(
        handler,
        "PUT",
        "/orders/order-001",
        {"amount": 2600, "status": "paid"},
    )
    assert updated["statusCode"] == 200
    assert json.loads(updated["body"]) == {
        "amount": 2600,
        "customer_id": "customer-001",
        "description": "Coffee beans",
        "order_id": "order-001",
        "status": "paid",
    }

    deleted = _invoke(handler, "DELETE", "/orders/order-001")
    assert deleted["statusCode"] == 200
    assert json.loads(deleted["body"]) == {
        "deleted": True,
        "order_id": "order-001",
    }

    missing = _invoke(handler, "GET", "/orders/order-001")
    assert missing["statusCode"] == 404
    assert json.loads(missing["body"]) == {"message": "Order not found."}

    assert (
        read_s3_json(
            s3_client,
            integration_bucket,
            "api-orders/order-001/created.json",
        )["action"]
        == "created"
    )
    assert (
        read_s3_json(
            s3_client,
            integration_bucket,
            "api-orders/order-001/updated.json",
        )["order"]["amount"]
        == 2600
    )
    assert (
        read_s3_json(
            s3_client,
            integration_bucket,
            "api-orders/order-001/deleted.json",
        )["action"]
        == "deleted"
    )


def test_api_rejects_invalid_bearer_token() -> None:
    handler: Any = importlib.import_module("sample_api_handler_app.handler")
    handler = importlib.reload(handler)

    response = handler.lambda_handler(
        _event(
            "GET",
            "/orders/order-001",
            authorization="Bearer wrong-token",
        ),
        None,
    )

    assert response["statusCode"] == 401
    assert json.loads(response["body"]) == {"message": "Unauthorized."}


def _invoke(
    handler: Any,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = handler.lambda_handler(_event(method, path, body), None)
    return dict(response)


def _event(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    authorization: str = "Bearer integration-token",
) -> dict[str, Any]:
    event = {
        "version": "2.0",
        "rawPath": path,
        "headers": {"authorization": authorization},
        "pathParameters": (
            {"order_id": path.removeprefix("/orders/")}
            if path.startswith("/orders/")
            else {}
        ),
        "requestContext": {"http": {"method": method}},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event
