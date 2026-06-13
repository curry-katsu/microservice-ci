from sample_eventbridge_handler_app.handler import lambda_handler


def test_lambda_handler_returns_event_summary() -> None:
    event = {
        "id": "event-1",
        "source": "sample.source",
        "detail-type": "SampleCreated",
        "detail": {"message": "hello"},
    }

    response = lambda_handler(event, context=None)

    assert response == {
        "ok": True,
        "event_id": "event-1",
        "source": "sample.source",
        "detail_type": "SampleCreated",
    }
