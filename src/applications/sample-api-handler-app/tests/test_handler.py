import importlib
import json
from typing import Any

from pytest import MonkeyPatch


def test_lambda_handler_rejects_missing_authorization(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_AUTH_TOKEN", "unit-token")

    handler: Any = importlib.import_module("sample_api_handler_app.handler")
    handler = importlib.reload(handler)

    response = handler.lambda_handler(
        _event("GET", "/orders/order-001", authorization=""),
        None,
    )

    assert response["statusCode"] == 401
    assert json.loads(response["body"]) == {"message": "Unauthorized."}


def test_lambda_handler_routes_create_order(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("API_AUTH_TOKEN", "unit-token")

    handler: Any = importlib.import_module("sample_api_handler_app.handler")
    handler = importlib.reload(handler)

    captured: dict[str, Any] = {}

    def fake_create_order(body: dict[str, Any]) -> dict[str, Any]:
        captured.update(body)
        return {
            "order_id": "order-001",
            "customer_id": body["customer_id"],
            "description": body["description"],
            "amount": body["amount"],
            "status": "pending",
        }

    monkeypatch.setattr(handler, "_create_order", fake_create_order)

    response = handler.lambda_handler(
        _event(
            "POST",
            "/orders",
            {
                "customer_id": "customer-001",
                "description": "Coffee beans",
                "amount": 2400,
            },
        ),
        None,
    )

    assert response["statusCode"] == 201
    assert captured == {
        "customer_id": "customer-001",
        "description": "Coffee beans",
        "amount": 2400,
    }
    assert json.loads(response["body"]) == {
        "amount": 2400,
        "customer_id": "customer-001",
        "description": "Coffee beans",
        "order_id": "order-001",
        "status": "pending",
    }


def _event(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    authorization: str = "Bearer unit-token",
) -> dict[str, Any]:
    event = {
        "version": "2.0",
        "rawPath": path,
        "headers": {"authorization": authorization} if authorization else {},
        "requestContext": {"http": {"method": method}},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event
