from typing import Any

from infra_core import EventBridgeEnvelope


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    envelope = EventBridgeEnvelope.from_event(event)
    return {
        "ok": True,
        "event_id": envelope.event_id,
        "source": envelope.source,
        "detail_type": envelope.detail_type,
    }
