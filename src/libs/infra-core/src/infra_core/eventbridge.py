from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EventBridgeEnvelope:
    event_id: str
    source: str
    detail_type: str
    detail: dict[str, Any]

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> "EventBridgeEnvelope":
        return cls(
            event_id=str(event.get("id", "")),
            source=str(event.get("source", "")),
            detail_type=str(event.get("detail-type", "")),
            detail=_as_dict(event.get("detail", {})),
        )


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
