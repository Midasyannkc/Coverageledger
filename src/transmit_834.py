"""
Transmit 834 enrollment files per client, writing to an SFTP-equivalent
outbox (local filesystem here; real SFTP documented as the production
target in docs/cost-tradeoffs.md) and recording each transmission in a
MongoDB transmission_ledger collection.
"""
from pathlib import Path

from src.x12_834_generator import build_834

OUTBOX = Path(__file__).resolve().parents[1] / "data" / "outbox"


def _events_for_client(db, group_code: str):
    client = db.clients.find_one({"group_code": group_code})
    events = list(db.enrollment_events.find({"group_code": {"$in": [group_code, client["ein"]]}}))
    members_by_id = {m["member_id"]: m for m in db.members.find({"group_code": group_code})}
    joined = []
    for ev in events:
        m = members_by_id.get(ev["member_id"])
        if not m:
            continue
        joined.append({**ev, "subscriber_id": m["subscriber_id"], "relationship_code": m["relationship_code"]})
    return client, joined


def transmit_naive(db, group_code: str, control_number: int, *, simulate_timeout_once: bool = False):
    """
    Naive transmitter: on a simulated timeout during the SFTP write, the
    caller's retry loop calls this function again. It does not check
    whether the termination it's about to send was already logged as sent,
    so a retried termination is logged (and "transmitted") a second time.
    """
    client, events = _events_for_client(db, group_code)
    term_events = [e for e in events if e["event_type"] == "terminate"]
    if not term_events:
        return 0

    OUTBOX.mkdir(parents=True, exist_ok=True)
    x12 = build_834(client, term_events, control_number=control_number)

    if simulate_timeout_once:
        # Simulate: the first write attempt times out AFTER the ledger
        # write already succeeded (a real, common failure mode -- the
        # network call fails but the side effect already landed), so the
        # caller's retry re-runs this whole function from the top.
        for ev in term_events:
            db.transmission_ledger.insert_one(
                {
                    "member_id": ev["member_id"],
                    "event_type": ev["event_type"],
                    "effective_date": ev["effective_date"],
                    "group_code": group_code,
                    "control_number": control_number,
                }
            )
        raise TimeoutError("simulated SFTP timeout after ledger write")

    out_path = OUTBOX / f"{group_code}_{control_number}.834"
    out_path.write_text(x12)
    for ev in term_events:
        db.transmission_ledger.insert_one(
            {
                "member_id": ev["member_id"],
                "event_type": ev["event_type"],
                "effective_date": ev["effective_date"],
                "group_code": group_code,
                "control_number": control_number,
            }
        )
    return len(term_events)
