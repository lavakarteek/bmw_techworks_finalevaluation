"""Validate telemetry and publish alerts for critical vehicle events."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

try:
    from .config import critical_fault_codes, temperature_threshold
except ImportError:
    from config import critical_fault_codes, temperature_threshold


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InvalidTelemetry(ValueError):
    """Raised when a telemetry event cannot be processed safely."""


def validate_telemetry(event: dict[str, Any]) -> dict[str, Any]:
    """Validate the fields and value ranges of a telemetry event.

    :param event: Telemetry payload containing ``event_id``, ``vehicle_id``,
        ``timestamp``, and numeric ``temperature`` fields.
    :returns: The original event after validation.
    :raises InvalidTelemetry: If a required field is missing or has an invalid
        value.
    """
    required_fields = {"event_id", "vehicle_id", "timestamp", "temperature"}
    missing_fields = sorted(required_fields - event.keys())
    if missing_fields:
        raise InvalidTelemetry(f"Missing fields: {', '.join(missing_fields)}")

    if not isinstance(event["event_id"], str) or not event["event_id"].strip():
        raise InvalidTelemetry("event_id must be a non-empty string")
    if not isinstance(event["vehicle_id"], str) or not event["vehicle_id"].strip():
        raise InvalidTelemetry("vehicle_id must be a non-empty string")
    if not isinstance(event["temperature"], (int, float)):
        raise InvalidTelemetry("temperature must be numeric")
    if not -50 <= float(event["temperature"]) <= 200:
        raise InvalidTelemetry("temperature is outside the valid range")

    try:
        datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise InvalidTelemetry("timestamp must be ISO-8601") from error
    return event


def evaluate_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Evaluate one event against the configured alert rules.

    An event is critical when its temperature meets the configured threshold
    or its fault code is in the configured critical fault-code set. Normal
    events return ``None``.

    :param event: Validated or unvalidated telemetry event.
    :returns: An alert record for a critical event, otherwise ``None``.
    :raises InvalidTelemetry: If the event fails telemetry validation.
    :raises ValueError: If an environment-based configuration value is invalid.
    """
    validated_event = validate_telemetry(event)
    fault_code = validated_event.get("fault_code")
    threshold = temperature_threshold()
    critical_fault = fault_code in critical_fault_codes()
    high_temperature = float(validated_event["temperature"]) >= threshold
    if not high_temperature and not critical_fault:
        return None

    return {
        "alert_id": f"alert-{validated_event['event_id']}",
        "event_id": validated_event["event_id"],
        "vehicle_id": validated_event["vehicle_id"],
        "temperature": validated_event["temperature"],
        "fault_code": fault_code,
        "timestamp": validated_event["timestamp"],
        "reasons": [
            reason
            for reason, matched in (
                ("HIGH_TEMPERATURE", high_temperature),
                ("CRITICAL_FAULT", critical_fault),
            )
            if matched
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _aws_clients() -> tuple[Any, Any]:
    """Create the AWS clients used to publish and audit alerts.

    :returns: An SNS client followed by an S3 client.
    """
    import boto3

    return boto3.client("sns"), boto3.client("s3")


def _write_outputs(alert: dict[str, Any], sns_client: Any, s3_client: Any) -> None:
    """Publish an alert notification and store its audit record.

    The SNS topic is read from ``SNS_TOPIC_ARN`` and the S3 bucket is read
    from ``AUDIT_BUCKET``. Audit records are stored under
    ``alerts/<event_id>.json``.

    :param alert: Alert record returned by :func:`evaluate_event`.
    :param sns_client: Boto3 SNS client or compatible test double.
    :param s3_client: Boto3 S3 client or compatible test double.
    :raises KeyError: If a required AWS environment variable is missing.
    """
    sns_client.publish(
        TopicArn=os.environ["SNS_TOPIC_ARN"],
        Subject=f"BMW critical vehicle alert: {alert['vehicle_id']}",
        Message=json.dumps(alert),
    )
    s3_client.put_object(
        Bucket=os.environ["AUDIT_BUCKET"],
        Key=f"alerts/{alert['event_id']}.json",
        Body=json.dumps(alert).encode("utf-8"),
        ContentType="application/json",
    )


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, int]:
    """Process telemetry records delivered by an SQS event source.

    Each record's ``body`` must contain a JSON telemetry event. Critical
    events are published to SNS and written to S3; normal events are only
    counted. Invalid records are logged and re-raised so SQS/Lambda retry and
    dead-letter behavior can handle them.

    :param event: AWS Lambda event containing an optional ``Records`` list.
    :param context: Lambda runtime context, accepted for the handler contract.
    :returns: Counts for processed, alerted, and rejected records.
    :raises KeyError: If an SQS record does not contain ``body``.
    :raises InvalidTelemetry: If a record contains invalid telemetry.
    :raises json.JSONDecodeError: If a record body is not valid JSON.
    """
    sns_client, s3_client = _aws_clients()
    processed = 0
    alerts_created = 0
    rejected = 0

    for record in event.get("Records", []):
        try:
            telemetry = json.loads(record["body"])
            alert = evaluate_event(telemetry)
            processed += 1
            if alert:
                _write_outputs(alert, sns_client, s3_client)
                alerts_created += 1
                logger.warning(json.dumps({"metric": "critical_alert", "alert_id": alert["alert_id"]}))
        except (KeyError, json.JSONDecodeError, InvalidTelemetry, TypeError, ValueError) as error:
            rejected += 1
            logger.error(json.dumps({"metric": "rejected_event", "error": str(error)}))
            raise

    logger.info(json.dumps({"metric": "telemetry_processed", "processed": processed, "alerts_created": alerts_created}))
    return {"processed": processed, "alerts_created": alerts_created, "rejected": rejected}