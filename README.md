Sphinx Documentation Link:https://lavakarteek.github.io/bmw_techworks_finalevaluation/usage.html

# BMW Vehicle Overheating and Fault Alert

Participant 2 capstone implementation: detect dangerous telemetry, publish an alert, and write an audit record.

## Business rule

An event is critical when either condition is true:

```text
temperature >= TEMPERATURE_THRESHOLD
OR fault_code is in CRITICAL_FAULT_CODES
```

The default temperature threshold is 85 degrees C. It is configurable through the `TEMPERATURE_THRESHOLD` Lambda environment variable, so the trainer can request a live change to 90 degrees C.

## Architecture

```text
Telemetry event -> SQS -> Lambda/Python -> SNS alert
                              |
                              +-> S3 JSON audit record
                              +-> CloudWatch logs and metrics
```

Terraform provisions SQS, SNS, S3, Lambda, least-privilege IAM policies, and CloudWatch logging.

## Local run

From PowerShell:

```powershell
\.\vehicleenv\Scripts\Activate.ps1
python -m pytest
python -m src.local_demo
```

The local demo evaluates a critical event without requiring AWS credentials.

## Terraform

```powershell
terraform -chdir=terraform init
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var="aws_region=us-east-1"
```

Do not run `terraform apply` until the trainer provides the AWS account, region, and permission boundary. Never commit AWS credentials.

## Test scenarios

- Temperature at or above the threshold creates an alert.
- A critical fault creates an alert even below the temperature threshold.
- A normal event creates no alert and no audit record.
- Missing or invalid telemetry is rejected with an error log.
- The threshold can be changed through configuration.

## Definition of Done evidence

- Source: SQS telemetry event.
- Processing: Python validation and business rule.
- Output: SNS alert and S3 audit record.
- Testing: five automated tests in `tests/`.
- Monitoring: structured logs and CloudWatch metric filter for critical alerts.
- Recovery: SQS redrive policy sends repeatedly failing messages to a dead-letter queue.
