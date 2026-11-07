from datetime import timedelta

import pytest

from tests.factories import event_fields, event_payload


def test_event_fields_are_valid_by_default() -> None:
    fields = event_fields()

    assert fields["occurred_at"].utcoffset() == timedelta(hours=7)
    assert fields["local_sequence"] >= 0
    assert fields["schema_version"] == 1


def test_event_fields_apply_overrides() -> None:
    assert event_fields(local_sequence=7)["local_sequence"] == 7


def test_event_fields_reject_unknown_names() -> None:
    with pytest.raises(TypeError, match="localSequence"):
        event_fields(localSequence=7)


def test_event_payload_uses_camel_case_and_keeps_offset() -> None:
    payload = event_payload()

    assert payload["eventId"] == str(event_fields()["event_id"])
    assert payload["occurredAt"] == "2026-11-03T07:58:12.345+07:00"


def test_event_payload_allows_malformed_and_extra_values() -> None:
    payload = event_payload(occurredAt="2026-11-03T07:58:12", agentVersion="2.0")

    assert payload["occurredAt"] == "2026-11-03T07:58:12"
    assert payload["agentVersion"] == "2.0"
