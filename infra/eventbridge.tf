resource "aws_cloudwatch_event_bus" "demo" {
  name = "${var.project_name}-bus"

  tags = {
    Name = "${var.project_name}-bus"
  }
}

resource "aws_cloudwatch_event_rule" "export_requested" {
  name           = "${var.project_name}-export-requested"
  description    = "Route export requests to Lambda processor"
  event_bus_name = aws_cloudwatch_event_bus.demo.name

  event_pattern = jsonencode({
    source      = ["demo.exports"]
    detail-type = ["ExportRequested"]
  })

  tags = {
    Name = "${var.project_name}-export-requested-rule"
  }
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule           = aws_cloudwatch_event_rule.export_requested.name
  event_bus_name = aws_cloudwatch_event_bus.demo.name
  arn            = aws_lambda_function.event_processor.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.event_processor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.export_requested.arn
}
