"""
Generate real X12 834 (Benefit Enrollment and Maintenance) segments from
MongoDB enrollment_events, built against the real segment layout and
qualifier codes documented in docs/x12_834_spec_notes.md (sourced from the
real DC HBX 834 Companion Guide -- see data/bronze/SOURCE.md).

Scope: ISA/GS/ST/BGN/N1/INS/REF/DTP/SE/GE/IEA for add ("021") and
terminate ("024") maintenance events. One ST...SE transaction set per
client (group), one INS loop per member event.
"""
from datetime import datetime

SENDER_TAX_ID = "741234500"  # synthetic TPA (CoverageLedger) tax ID
SEGMENT_SEP = "~"
ELEMENT_SEP = "*"


def _seg(*elements) -> str:
    return ELEMENT_SEP.join(str(e) for e in elements) + SEGMENT_SEP


def build_834(client: dict, events: list[dict], *, control_number: int, usage: str = "T") -> str:
    """
    Build one real X12 834 interchange (ISA...IEA) for a single client's
    enrollment events. `events` is a list of enrollment_events documents,
    each already joined to its member record (expects member_id,
    subscriber_id, relationship_code, event_type, effective_date).
    """
    now = datetime.utcnow()
    isa_date = now.strftime("%y%m%d")
    isa_time = now.strftime("%H%M")
    gs_date = now.strftime("%Y%m%d")

    segments = []
    segments.append(
        _seg(
            "ISA", "00", " " * 10, "00", " " * 10, "30", SENDER_TAX_ID.rjust(15),
            "30", client["ein"].rjust(15), isa_date, isa_time, "^", "00501",
            f"{control_number:09d}", "1", usage, ":",
        )
    )
    segments.append(_seg("GS", "BE", SENDER_TAX_ID, client["ein"], gs_date, isa_time, str(control_number), "X", "005010X220A1"))
    segments.append(_seg("ST", "834", f"{control_number:04d}"))
    segments.append(_seg("BGN", "00", f"{control_number:04d}", now.strftime("%Y%m%d"), now.strftime("%H%M"), "2"))

    # Loop 1000A: Plan Sponsor (the TPA, CoverageLedger)
    segments.append(_seg("N1", "P5", "CoverageLedger TPA", "FI", SENDER_TAX_ID))
    # Loop 1000B: Payer/Carrier -- here, the client (employer group) itself
    segments.append(_seg("N1", "IN", client["name"], "FI", client["ein"]))

    for ev in events:
        maint_code = "021" if ev["event_type"] == "add" else "024"
        ins_response = "Y" if ev.get("relationship_code") == "subscriber" else "N"
        segments.append(_seg("INS", ins_response, "18" if ins_response == "N" else "18", maint_code, "EC", "A"))
        segments.append(_seg("REF", "0F", ev["subscriber_id"]))
        segments.append(_seg("REF", "23", ev["member_id"]))
        segments.append(_seg("DTP", "303", "D8", ev["effective_date"].strftime("%Y%m%d")))

    se_segment_count = len(segments) - 2  # ST through the segment before SE, plus SE itself
    segments.append(_seg("SE", se_segment_count + 1, f"{control_number:04d}"))
    segments.append(_seg("GE", "1", str(control_number)))
    segments.append(_seg("IEA", "1", f"{control_number:09d}"))

    return "".join(segments)


def parse_ins_events(x12_text: str) -> list[dict]:
    """Minimal reverse-parser used by tests to verify round-trip fidelity."""
    out = []
    pending = {}
    for raw_seg in x12_text.split(SEGMENT_SEP):
        if not raw_seg:
            continue
        parts = raw_seg.split(ELEMENT_SEP)
        if parts[0] == "INS":
            if pending:
                out.append(pending)
            pending = {"maintenance_type_code": parts[3]}
        elif parts[0] == "REF" and parts[1] == "23":
            pending["member_id"] = parts[2]
        elif parts[0] == "DTP" and parts[1] == "303":
            pending["effective_date"] = parts[3]
    if pending:
        out.append(pending)
    return out
