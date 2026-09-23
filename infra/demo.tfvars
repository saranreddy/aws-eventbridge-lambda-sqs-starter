# Demo configuration with cheap defaults

aws_region    = "us-east-1"
environment   = "demo"
project_name  = "eventbridge-lambda-sqs-demo"

lambda_timeout     = 30
lambda_memory_size = 256

sqs_visibility_timeout = 60
sqs_message_retention  = 345600
sqs_max_receive_count  = 3
