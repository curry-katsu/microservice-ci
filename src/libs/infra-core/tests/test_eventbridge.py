from infra_core import EventBridgeEnvelope


def test_eventbridge_envelope_from_event() -> None:
    event = {
        "id": "event-1",
        "source": "sample.source",
        "detail-type": "SampleCreated",
        "detail": {"message": "hello"},
    }

    envelope = EventBridgeEnvelope.from_event(event)

    assert envelope.event_id == "event-1"
    assert envelope.source == "sample.source"
    assert envelope.detail_type == "SampleCreated"
    assert envelope.detail == {"message": "hello"}
