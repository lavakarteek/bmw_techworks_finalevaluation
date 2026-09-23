"""Configuration helpers for telemetry alert evaluation.

Values are read from environment variables so the same application code can
be used locally and in AWS Lambda.
"""

import os


DEFAULT_TEMPERATURE_THRESHOLD = 85.0
DEFAULT_CRITICAL_FAULT_CODES = {"BATTERY_OVERHEAT", "THERMAL_RUNAWAY", "COOLING_FAILURE"}


def temperature_threshold() -> float:
    """Return the configured critical temperature threshold in Celsius.

    The ``TEMPERATURE_THRESHOLD`` environment variable overrides the default
    value of 85 degrees Celsius.

    :returns: The temperature at or above which an event is critical.
    :raises ValueError: If ``TEMPERATURE_THRESHOLD`` is not numeric.
    """
    return float(os.getenv("TEMPERATURE_THRESHOLD", DEFAULT_TEMPERATURE_THRESHOLD))


def critical_fault_codes() -> set[str]:
    """Return the configured fault codes that always create an alert.

    ``CRITICAL_FAULT_CODES`` is a comma-separated environment variable. Empty
    entries are ignored. When the variable is unset, the default critical
    fault-code set is returned.

    :returns: A set of fault-code strings that require an alert.
    """
    raw_codes = os.getenv("CRITICAL_FAULT_CODES")
    if not raw_codes:
        return DEFAULT_CRITICAL_FAULT_CODES
    return {code.strip() for code in raw_codes.split(",") if code.strip()}