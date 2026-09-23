import json

import pytest

from src.alert_service import InvalidTelemetry, evaluate_event, lambda_handler


def telemetry(**overrides):
    """Build a valid baseline telemetry event with optional overrides."""
    event = {
        "event_id": "evt-1",
        "vehicle_id": "BMW-001",
        "timestamp": "2026-09-17T09:00:00Z",
        "temperature": 70,
        "fault_code": None,
    }
    event.update(overrides)
    return event


def test_high_temperature_creates_alert():
    """Verify that temperature at the threshold creates an alert."""
    alert = evaluate_event(telemetry(temperature=85))
    assert alert["reasons"] == ["HIGH_TEMPERATURE"]


def test_critical_fault_creates_alert_below_threshold():
    """Verify that a critical fault creates an alert below the threshold."""
    alert = evaluate_event(telemetry(fault_code="THERMAL_RUNAWAY"))
    assert alert["reasons"] == ["CRITICAL_FAULT"]


def test_normal_event_creates_no_alert():
    """Verify that ordinary telemetry does not create an alert."""
    assert evaluate_event(telemetry()) is None


def test_invalid_event_is_rejected():
    """Verify that invalid telemetry raises the validation exception."""
    with pytest.raises(InvalidTelemetry):
        evaluate_event(telemetry(temperature="hot"))


def test_lambda_publishes_alert_and_writes_audit(monkeypatch):
    """Verify that a critical Lambda event reaches SNS and S3."""
    published = []
    written = []

    class FakeSns:
        def publish(self, **kwargs):
            """Record the SNS publish request for assertions."""
            published.append(kwargs)

    class FakeS3:
        def put_object(self, **kwargs):
            """Record the S3 write request for assertions."""
            written.append(kwargs)

    monkeypatch.setattr("src.alert_service._aws_clients", lambda: (FakeSns(), FakeS3()))
    monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123:alerts")
    monkeypatch.setenv("AUDIT_BUCKET", "audit-bucket")
    result = lambda_handler({"Records": [{"body": json.dumps(telemetry(temperature=90))}]})
    assert result == {"processed": 1, "alerts_created": 1, "rejected": 0}
    assert len(published) == 1
    assert written[0]["Key"] == "alerts/evt-1.json"