resource "aws_sqs_queue" "sample_events" {
  name = "sample-events"
}

resource "aws_cloudwatch_event_bus" "sample" {
  name = "sample-event-bus"
}
