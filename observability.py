"""Safe structured logging helpers for application diagnostics."""

import json


SAFE_FIELDS = {
    "exception_type",
    "operation",
    "status_code",
    "provider",
    "route",
}


def log_event(logger, level, event, **fields):
    """Emit a JSON event while allowing only non-sensitive diagnostic fields."""
    payload = {"event": event}
    for name, value in fields.items():
        if name in SAFE_FIELDS and isinstance(value, (bool, int, float, str)):
            payload[name] = value
    logger.log(level, json.dumps(payload, sort_keys=True))
