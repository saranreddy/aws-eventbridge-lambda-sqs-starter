resource "aws_sqs_queue" "failed_events_dlq" {
  name                       = "${var.project_name}-failed-events-dlq"
  message_retention_seconds  = var.sqs_message_retention
  visibility_timeout_seconds = var.sqs_visibility_timeout

  tags = {
    Name = "${var.project_name}-failed-events-dlq"
  }
}

resource "aws_sqs_queue" "failed_events" {
  name                       = "${var.project_name}-failed-events"
  message_retention_seconds  = var.sqs_message_retention
  visibility_timeout_seconds = var.sqs_visibility_timeout

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.failed_events_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  tags = {
    Name = "${var.project_name}-failed-events"
  }
}

resource "aws_sqs_queue_policy" "failed_events" {
  queue_url = aws_sqs_queue.failed_events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaToSendMessages"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.failed_events.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_lambda_function.event_processor.arn
          }
        }
      }
    ]
  })
}
