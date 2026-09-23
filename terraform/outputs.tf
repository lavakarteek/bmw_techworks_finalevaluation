output "telemetry_queue_url" {
  value = aws_sqs_queue.telemetry.url
}

output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "audit_bucket_name" {
  value = aws_s3_bucket.audit.id
}