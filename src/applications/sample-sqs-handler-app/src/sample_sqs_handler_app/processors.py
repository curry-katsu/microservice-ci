import json
import os
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0
    retryable_errors: list[str] = field(default_factory=lambda: ["ThrottlingException"])


@dataclass
class MessageMetadata:
    message_id: str
    event_source: str
    receipt_handle: str
    approximate_receive_count: int
    sent_timestamp: str
    attributes: dict[str, str]


@dataclass
class ProcessResult:
    message_id: str
    success: bool
    s3_key: str | None = None
    error: str | None = None
    retry_count: int = 0


class MessageValidator:
    REQUIRED_FIELDS = ["messageId", "eventSource", "body"]

    def validate(self, record: dict[str, Any]) -> tuple[bool, list[str]]:
        errors: list[str] = []
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in record:
                errors.append(f"missing required field: {field_name}")
        body = record.get("body", "")
        if not isinstance(body, str):
            errors.append("body must be a string")
        message_id = record.get("messageId", "")
        if not isinstance(message_id, str) or not message_id:
            errors.append("messageId must be a non-empty string")
        return len(errors) == 0, errors

    def validate_batch(self, records: list[dict[str, Any]]) -> dict[str, list[str]]:
        results: dict[str, list[str]] = {}
        for record in records:
            message_id = str(record.get("messageId", "unknown"))
            _, errors = self.validate(record)
            if errors:
                results[message_id] = errors
        return results


class BodyParser:
    def parse(self, body: str) -> Any:
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body

    def parse_nested(self, body: str, depth: int = 3) -> Any:
        result = self.parse(body)
        if depth <= 0 or not isinstance(result, dict):
            return result
        for key, value in result.items():
            if isinstance(value, str):
                result[key] = self.parse_nested(value, depth - 1)
        return result

    def extract_fields(self, body: str, fields: list[str]) -> dict[str, Any]:
        parsed = self.parse(body)
        if not isinstance(parsed, dict):
            return {}
        return {f: parsed[f] for f in fields if f in parsed}


class S3KeyBuilder:
    def __init__(
        self,
        prefix: str = "sqs-messages",
        partition_by_date: bool = False,
    ) -> None:
        self._prefix = prefix
        self._partition_by_date = partition_by_date

    def build(self, message_id: str, event_source: str | None = None) -> str:
        parts = [self._prefix]
        if self._partition_by_date:
            ts = str(int(time.time()))
            parts.append(ts[:8])
        if event_source:
            safe_source = event_source.replace(":", "_").replace("/", "_")
            parts.append(safe_source)
        parts.append(f"{message_id}.json")
        return "/".join(parts)

    def build_batch(self, message_ids: list[str]) -> list[str]:
        return [self.build(mid) for mid in message_ids]


class RetryHandler:
    def __init__(self, config: RetryConfig | None = None) -> None:
        self._config = config or RetryConfig()

    def should_retry(self, error_code: str, attempt: int) -> bool:
        if attempt >= self._config.max_attempts:
            return False
        return error_code in self._config.retryable_errors

    def wait_seconds(self, attempt: int) -> float:
        return self._config.base_delay * (self._config.backoff_factor**attempt)

    def execute(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(self._config.max_attempts):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_code = type(e).__name__
                if not self.should_retry(error_code, attempt + 1):
                    raise
                time.sleep(self.wait_seconds(attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError("retry exhausted with no error captured")


class DeadLetterReporter:
    def __init__(self, dlq_url: str | None = None) -> None:
        self._dlq_url = dlq_url or os.environ.get("DLQ_URL", "")

    def is_configured(self) -> bool:
        return bool(self._dlq_url)

    def build_failure_payload(
        self, record: dict[str, Any], error: str
    ) -> dict[str, Any]:
        return {
            "original_message_id": str(record.get("messageId", "")),
            "original_event_source": str(record.get("eventSource", "")),
            "error": error,
            "failed_at": str(int(time.time())),
        }

    def format_for_dlq(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False)


class MetricsCollector:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._timings: dict[str, list[float]] = {}

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def record_timing(self, name: str, elapsed: float) -> None:
        if name not in self._timings:
            self._timings[name] = []
        self._timings[name].append(elapsed)

    def average_timing(self, name: str) -> float | None:
        timings = self._timings.get(name)
        if not timings:
            return None
        return sum(timings) / len(timings)

    def summary(self) -> dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "timings": {
                k: {
                    "count": len(v),
                    "avg": sum(v) / len(v),
                    "min": min(v),
                    "max": max(v),
                }
                for k, v in self._timings.items()
                if v
            },
        }


def extract_metadata(record: dict[str, Any]) -> MessageMetadata:
    attrs = record.get("attributes", {})
    return MessageMetadata(
        message_id=str(record.get("messageId", "")),
        event_source=str(record.get("eventSource", "")),
        receipt_handle=str(record.get("receiptHandle", "")),
        approximate_receive_count=int(attrs.get("ApproximateReceiveCount", 0)),
        sent_timestamp=str(attrs.get("SentTimestamp", "")),
        attributes={k: str(v) for k, v in attrs.items()},
    )


def filter_records(
    records: list[dict[str, Any]],
    event_source: str,
) -> list[dict[str, Any]]:
    return [r for r in records if r.get("eventSource") == event_source]


def group_by_source(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        source = str(record.get("eventSource", "unknown"))
        if source not in groups:
            groups[source] = []
        groups[source].append(record)
    return groups


def sanitize_message_id(message_id: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return "".join(c if c in allowed else "_" for c in message_id)


def build_s3_key(message_id: str, prefix: str = "sqs-messages") -> str:
    safe_id = sanitize_message_id(message_id)
    return f"{prefix}/{safe_id}.json"


def serialize_record(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, default=str)


def deserialize_record(raw: str) -> dict[str, Any]:
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError(f"expected dict, got {type(result).__name__}")
    return result


def chunk_records(records: list[Any], size: int) -> list[list[Any]]:
    return [records[i : i + size] for i in range(0, len(records), size)]
