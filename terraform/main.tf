data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_s3_bucket" "audit" {
  bucket_prefix = "bmw-vehicle-alert-audit-"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_sqs_queue" "dead_letter" {
  name                      = "bmw-vehicle-alert-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "telemetry" {
  name                       = "bmw-vehicle-telemetry"
  visibility_timeout_seconds = 180

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sns_topic" "alerts" {
  name = "bmw-critical-vehicle-alerts"
}

resource "aws_iam_role" "lambda" {
  name = "bmw-vehicle-alert-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda" {
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/bmw-vehicle-alert:*"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.telemetry.arn
      },
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.alerts.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.audit.arn}/alerts/*"
      }
    ]
  })
}

resource "aws_lambda_function" "alert" {
  function_name    = "bmw-vehicle-alert"
  role             = aws_iam_role.lambda.arn
  handler          = "alert_service.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  timeout          = 60

  environment {
    variables = {
      SNS_TOPIC_ARN        = aws_sns_topic.alerts.arn
      AUDIT_BUCKET         = aws_s3_bucket.audit.id
      TEMPERATURE_THRESHOLD = tostring(var.temperature_threshold)
      CRITICAL_FAULT_CODES = var.critical_fault_codes
    }
  }
}

resource "aws_lambda_event_source_mapping" "telemetry" {
  event_source_arn = aws_sqs_queue.telemetry.arn
  function_name    = aws_lambda_function.alert.arn
  batch_size       = 10
}

resource "aws_cloudwatch_log_group" "alert" {
  name              = "/aws/lambda/${aws_lambda_function.alert.function_name}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_metric_filter" "critical_alerts" {
  name           = "bmw-critical-alert-count"
  pattern        = "{ $.metric = \"critical_alert\" }"
  log_group_name = aws_cloudwatch_log_group.alert.name

  metric_transformation {
    name      = "CriticalAlertCount"
    namespace = "BMW/VehicleAlerts"
    value     = "1"
  }
}