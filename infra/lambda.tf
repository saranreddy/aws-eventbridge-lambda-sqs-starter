data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambda"
  output_path = "${path.module}/.terraform/lambda_function.zip"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-processor"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-lambda-logs"
  }
}

resource "aws_lambda_function" "event_processor" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-processor"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      FAILED_QUEUE_URL = aws_sqs_queue.failed_events.url
      ENVIRONMENT      = var.environment
      PROJECT_NAME     = var.project_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_permissions
  ]

  tags = {
    Name = "${var.project_name}-event-processor"
  }
}

resource "aws_lambda_function_event_invoke_config" "event_processor" {
  function_name = aws_lambda_function.event_processor.function_name

  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 2

  destination_config {
    on_failure {
      destination = aws_sqs_queue.failed_events.arn
    }
  }
}
