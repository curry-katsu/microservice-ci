import json
from typing import Any


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    records = event.get("Records", [])
    messages = [
        _build_message_summary(record) for record in records if isinstance(record, dict)
    ]
    return {
        "ok": True,
        "record_count": len(messages),
        "messages": messages,
    }


def _build_message_summary(record: dict[str, Any]) -> dict[str, Any]:
    body = str(record.get("body", ""))
    return {
        "message_id": str(record.get("messageId", "")),
        "event_source": str(record.get("eventSource", "")),
        "body": _parse_body(body),
    }


def _parse_body(body: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body
