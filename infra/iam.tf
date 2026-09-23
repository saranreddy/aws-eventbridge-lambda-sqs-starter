data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda_execution" {
  name               = "${var.project_name}-lambda-execution"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Name = "${var.project_name}-lambda-execution-role"
  }
}

data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-processor*"
    ]
  }

  statement {
    sid    = "SendToSQS"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:GetQueueUrl"
    ]
    resources = [
      aws_sqs_queue.failed_events.arn
    ]
  }
}

resource "aws_iam_policy" "lambda_permissions" {
  name        = "${var.project_name}-lambda-permissions"
  description = "Permissions for event processor Lambda"
  policy      = data.aws_iam_policy_document.lambda_permissions.json
}

resource "aws_iam_role_policy_attachment" "lambda_permissions" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_permissions.arn
}
