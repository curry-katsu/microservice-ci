import json
import os
from typing import Any

from infra_core.aws.s3 import S3Client

_s3 = S3Client()
_BUCKET = os.environ["S3_BUCKET"]


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    records = event.get("Records", [])
    saved_keys: list[str] = []
    for record in records:
        if isinstance(record, dict):
            key = _save_record(record)
            saved_keys.append(key)
    return {
        "ok": True,
        "record_count": len(saved_keys),
        "saved_keys": saved_keys,
    }


def _save_record(record: dict[str, Any]) -> str:
    message_id = str(record.get("messageId", ""))
    payload: dict[str, Any] = {
        "message_id": message_id,
        "event_source": str(record.get("eventSource", "")),
        "body": _parse_body(str(record.get("body", ""))),
    }
    key = f"sqs-messages/{message_id}.json"
    _s3.put_object(
        bucket=_BUCKET,
        key=key,
        body=json.dumps(payload, ensure_ascii=False),
        content_type="application/json",
    )
    return key


def _parse_body(body: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body
