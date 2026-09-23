Configuration
=============

The alert service reads configuration from Lambda environment variables. The
same variables can be set locally when testing a different policy.

``TEMPERATURE_THRESHOLD``
	Defaults to ``85`` and sets the critical temperature in degrees Celsius.

``CRITICAL_FAULT_CODES``
	Defaults to ``BATTERY_OVERHEAT,THERMAL_RUNAWAY,COOLING_FAILURE`` and lists
	the comma-separated fault codes that always create an alert.

``SNS_TOPIC_ARN``
	Required in AWS. Identifies the SNS topic for alert notifications.

``AUDIT_BUCKET``
	Required in AWS. Identifies the S3 bucket for JSON audit records.

For Terraform deployments, ``temperature_threshold`` and
``critical_fault_codes`` are Terraform variables. The SNS topic ARN and audit
bucket name are injected into the Lambda environment automatically.

To inspect the deployed queue URL after Terraform creates the infrastructure:

.. code-block:: powershell

	terraform -chdir=terraform output telemetry_queue_url

The application uses that value as the ``--queue-url`` argument when sending
telemetry to SQS.

Security
--------

Do not commit AWS credentials or sensitive subscription details. Apply the
Terraform stack only in an AWS account with the required permission boundary
and review the generated IAM policies before deployment.
