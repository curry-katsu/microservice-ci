import json
import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from infra_core.aws.s3 import S3Client
from infra_core.rds.providers import RdsSessionProvider
from sqlalchemy import RowMapping, text


@dataclass(frozen=True)
class ApiRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: dict[str, Any]
    path_parameters: dict[str, str]


class ApiError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


_rds = RdsSessionProvider()
_s3 = S3Client()


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    del context
    try:
        request = _build_request(event)
        _authorize(request.headers)
        result = _route(request)
        return _response(result["status_code"], result["body"])
    except ApiError as error:
        return _response(error.status_code, {"message": error.message})


def _build_request(event: dict[str, Any]) -> ApiRequest:
    headers = {
        str(key).lower(): str(value)
        for key, value in (event.get("headers") or {}).items()
        if value is not None
    }
    body = _parse_body(event.get("body"))
    path_parameters = {
        str(key): str(value)
        for key, value in (event.get("pathParameters") or {}).items()
        if value is not None
    }

    http_context = event.get("requestContext", {}).get("http", {})
    raw_method = http_context.get("method") or event.get("httpMethod") or ""
    method = str(raw_method).upper()
    path = str(event.get("rawPath") or event.get("path") or "")
    if not method or not path:
        raise ApiError(400, "Invalid API Gateway event.")

    return ApiRequest(
        method=method,
        path=path,
        headers=headers,
        body=body,
        path_parameters=path_parameters,
    )


def _parse_body(raw_body: Any) -> dict[str, Any]:
    if raw_body in (None, ""):
        return {}
    if not isinstance(raw_body, str):
        raise ApiError(400, "Request body must be a JSON string.")
    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise ApiError(400, "Request body must be valid JSON.") from error
    if not isinstance(parsed, dict):
        raise ApiError(400, "Request body must be a JSON object.")
    return parsed


def _authorize(headers: dict[str, str]) -> None:
    expected_token = os.getenv("API_AUTH_TOKEN", "local-api-token")
    authorization = headers.get("authorization", "")
    if authorization != f"Bearer {expected_token}":
        raise ApiError(401, "Unauthorized.")


def _route(request: ApiRequest) -> dict[str, Any]:
    if request.method == "POST" and request.path == "/orders":
        return {"status_code": 201, "body": _create_order(request.body)}

    order_id = request.path_parameters.get("order_id") or _order_id_from_path(
        request.path
    )
    if order_id is None:
        raise ApiError(404, "Route not found.")

    if request.method == "GET":
        return {"status_code": 200, "body": _get_order(order_id)}
    if request.method == "PUT":
        return {
            "status_code": 200,
            "body": _update_order(order_id, request.body),
        }
    if request.method == "DELETE":
        _delete_order(order_id)
        return {
            "status_code": 200,
            "body": {"deleted": True, "order_id": order_id},
        }

    raise ApiError(405, "Method not allowed.")


def _order_id_from_path(path: str) -> str | None:
    prefix = "/orders/"
    if not path.startswith(prefix):
        return None
    order_id = path.removeprefix(prefix)
    if not order_id or "/" in order_id:
        return None
    return order_id


def _create_order(body: dict[str, Any]) -> dict[str, Any]:
    customer_id = _required_string(body, "customer_id")
    description = _required_string(body, "description")
    amount = _required_positive_int(body, "amount")
    order_id = str(body.get("order_id") or uuid4())

    with _rds.write_transaction() as session:
        session.execute(
            text(
                """
                INSERT INTO api_orders
                    (order_id, customer_id, description, amount)
                VALUES (:order_id, :customer_id, :description, :amount)
                """
            ),
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "description": description,
                "amount": amount,
            },
        )

    order = _get_order(order_id)
    _write_audit("created", order)
    return order


def _get_order(order_id: str) -> dict[str, Any]:
    with _rds.read_session() as session:
        row = (
            session.execute(
                text(
                    """
                SELECT order_id, customer_id, description, amount, status
                FROM api_orders
                WHERE order_id = :order_id
                """
                ),
                {"order_id": order_id},
            )
            .mappings()
            .first()
        )

    if row is None:
        raise ApiError(404, "Order not found.")
    return _row_to_order(row)


def _update_order(order_id: str, body: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if "description" in body:
        updates["description"] = _required_string(body, "description")
    if "amount" in body:
        updates["amount"] = _required_positive_int(body, "amount")
    if "status" in body:
        status = _required_string(body, "status")
        if status not in {"pending", "paid", "cancelled"}:
            raise ApiError(400, "status must be pending, paid, or cancelled.")
        updates["status"] = status
    if not updates:
        raise ApiError(400, "At least one updatable field is required.")

    assignments = ", ".join(f"{key} = :{key}" for key in updates)
    params = {"order_id": order_id, **updates}
    with _rds.write_transaction() as session:
        row = (
            session.execute(
                text(
                    f"""
                UPDATE api_orders
                SET {assignments}, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = :order_id
                RETURNING order_id, customer_id, description, amount, status
                """
                ),
                params,
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ApiError(404, "Order not found.")

    order = _row_to_order(row)
    _write_audit("updated", order)
    return order


def _delete_order(order_id: str) -> None:
    order = _get_order(order_id)
    with _rds.write_transaction() as session:
        session.execute(
            text("DELETE FROM api_orders WHERE order_id = :order_id"),
            {"order_id": order_id},
        )
    _write_audit("deleted", order)


def _required_string(body: dict[str, Any], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, f"{key} is required.")
    return value.strip()


def _required_positive_int(body: dict[str, Any], key: str) -> int:
    value = body.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ApiError(400, f"{key} must be a positive integer.")
    return value


def _row_to_order(row: RowMapping) -> dict[str, Any]:
    return {
        "order_id": str(row["order_id"]),
        "customer_id": str(row["customer_id"]),
        "description": str(row["description"]),
        "amount": int(row["amount"]),
        "status": str(row["status"]),
    }


def _write_audit(action: str, order: dict[str, Any]) -> None:
    bucket = os.getenv("AUDIT_BUCKET")
    if not bucket:
        return
    payload = {"action": action, "order": order}
    _s3.put_object(
        bucket=bucket,
        key=f"api-orders/{order['order_id']}/{action}.json",
        body=json.dumps(payload, ensure_ascii=False, sort_keys=True),
        content_type="application/json",
    )


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False, sort_keys=True),
    }
