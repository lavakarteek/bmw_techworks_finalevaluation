"""Run a single telemetry evaluation without requiring AWS credentials."""

import json

from .alert_service import evaluate_event


def main() -> None:
    """Evaluate and print one sample BMW telemetry event."""
    event = {
        "event_id": "demo-001",
        "vehicle_id": "BMW-EV-002",
        "timestamp": "2026-09-17T09:00:00Z",
        "temperature": 86.5,
        "fault_code": None,
    }
    print(json.dumps(evaluate_event(event), indent=2))


if __name__ == "__main__":
    main()