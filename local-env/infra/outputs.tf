output "sample_queue_url" {
  value = aws_sqs_queue.sample_events.url
}

output "sample_event_bus_name" {
  value = aws_cloudwatch_event_bus.sample.name
}
