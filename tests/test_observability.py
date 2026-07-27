import json
import logging

from observability import log_event


def test_log_event_emits_json_and_drops_sensitive_fields(caplog):
    logger = logging.getLogger("test.observability")

    with caplog.at_level(logging.WARNING, logger=logger.name):
        log_event(
            logger,
            logging.WARNING,
            "auth.failure",
            route="/login",
            exception_type="ValueError",
            password="must-not-appear",
            api_key="must-not-appear",
        )

    record = caplog.records[-1]
    payload = json.loads(record.message)
    assert payload == {
        "event": "auth.failure",
        "exception_type": "ValueError",
        "route": "/login",
    }
    assert "must-not-appear" not in record.message
