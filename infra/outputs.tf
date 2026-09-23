output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "event_bus_name" {
  description = "EventBridge custom bus name"
  value       = aws_cloudwatch_event_bus.demo.name
}

output "event_bus_arn" {
  description = "EventBridge custom bus ARN"
  value       = aws_cloudwatch_event_bus.demo.arn
}

output "event_rule_name" {
  description = "EventBridge rule name"
  value       = aws_cloudwatch_event_rule.export_requested.name
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.event_processor.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.event_processor.arn
}

output "lambda_log_group" {
  description = "Lambda CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "sqs_queue_url" {
  description = "SQS queue URL for failed events"
  value       = aws_sqs_queue.failed_events.url
}

output "sqs_queue_arn" {
  description = "SQS queue ARN for failed events"
  value       = aws_sqs_queue.failed_events.arn
}

output "sqs_dlq_url" {
  description = "SQS DLQ URL"
  value       = aws_sqs_queue.failed_events_dlq.url
}

output "sqs_dlq_arn" {
  description = "SQS DLQ ARN"
  value       = aws_sqs_queue.failed_events_dlq.arn
}
