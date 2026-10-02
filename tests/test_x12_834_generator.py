from datetime import datetime

from src.x12_834_generator import build_834, parse_ins_events

CLIENT = {"group_code": "GRP-01", "name": "Lakeshore Logistics", "ein": "741234561", "funding_type": "self-funded"}

EVENTS = [
    {
        "member_id": "MBR-00001",
        "subscriber_id": "MBR-00001",
        "relationship_code": "subscriber",
        "event_type": "add",
        "effective_date": datetime(2024, 1, 15),
    },
    {
        "member_id": "MBR-00002",
        "subscriber_id": "MBR-00001",
        "relationship_code": "dependent",
        "event_type": "add",
        "effective_date": datetime(2024, 1, 15),
    },
    {
        "member_id": "MBR-00001",
        "subscriber_id": "MBR-00001",
        "relationship_code": "subscriber",
        "event_type": "terminate",
        "effective_date": datetime(2024, 7, 1),
    },
]


def test_envelope_segments_present():
    x12 = build_834(CLIENT, EVENTS, control_number=1)
    for seg_id in ("ISA", "GS", "ST", "BGN", "N1", "INS", "REF", "DTP", "SE", "GE", "IEA"):
        assert f"{seg_id}*" in x12 or f"~{seg_id}~" in x12 or x12.startswith(f"{seg_id}*")


def test_real_maintenance_type_codes_used():
    x12 = build_834(CLIENT, EVENTS, control_number=1)
    # 021 = Addition (real code from the companion guide), 024 = Termination
    assert x12.count("*021*") == 2  # two adds
    assert x12.count("*024*") == 1  # one termination


def test_round_trip_member_ids_and_maintenance_codes():
    x12 = build_834(CLIENT, EVENTS, control_number=1)
    parsed = parse_ins_events(x12)
    assert len(parsed) == 3
    assert {p["member_id"] for p in parsed} == {"MBR-00001", "MBR-00002"}
    codes = sorted(p["maintenance_type_code"] for p in parsed)
    assert codes == ["021", "021", "024"]


def test_effective_dates_round_trip():
    x12 = build_834(CLIENT, EVENTS, control_number=1)
    parsed = parse_ins_events(x12)
    dates = {p["effective_date"] for p in parsed}
    assert "20240115" in dates
    assert "20240701" in dates
