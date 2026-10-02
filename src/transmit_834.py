"""
Transmit 834 enrollment files per client, writing to an SFTP-equivalent
outbox (local filesystem here; real SFTP documented as the production
target in docs/cost-tradeoffs.md) and recording each transmission in a
MongoDB transmission_ledger collection.

INCIDENT 1 (see docs/incidents.md): a naive retry-on-timeout policy
resent a termination after a simulated transient failure, without checking
whether that termination had already been logged as sent -- violating the
JD's explicit requirement to "guarantee a termination is sent exactly
once." Reproduced below with transmit_naive(), fixed with transmit().
"""
from pathlib import Path

from src.x12_834_generator import build_834

OUTBOX = Path(__file__).resolve().parents[1] / "data" / "outbox"


def _events_for_client(db, group_code: str):
    client = db.clients.find_one({"group_code": group_code})
    real_group_code = group_code
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

    attempt = {"simulated": True}
    if simulate_timeout_once and not attempt.get("_already_retried"):
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


def transmit(db, group_code: str, control_number: int):
    """
    FIX (Incident 1): idempotent transmission. A unique index on the
    natural key (member_id, event_type, effective_date) means a duplicate
    ledger write raises DuplicateKeyError instead of silently succeeding
    twice, so a retry after a successful-but-unacknowledged send is a
    no-op rather than a second real termination transmission.
    """
    db.transmission_ledger.create_index(
        [("member_id", 1), ("event_type", 1), ("effective_date", 1)], unique=True
    )
    client, events = _events_for_client(db, group_code)
    term_events = [e for e in events if e["event_type"] == "terminate"]
    if not term_events:
        return 0

    already_sent = {
        (r["member_id"], r["event_type"], r["effective_date"])
        for r in db.transmission_ledger.find({"group_code": group_code, "event_type": "terminate"})
    }
    to_send = [
        e for e in term_events
        if (e["member_id"], e["event_type"], e["effective_date"]) not in already_sent
    ]
    if not to_send:
        return 0

    OUTBOX.mkdir(parents=True, exist_ok=True)
    x12 = build_834(client, to_send, control_number=control_number)
    out_path = OUTBOX / f"{group_code}_{control_number}.834"
    out_path.write_text(x12)

    sent = 0
    for ev in to_send:
        try:
            db.transmission_ledger.insert_one(
                {
                    "member_id": ev["member_id"],
                    "event_type": ev["event_type"],
                    "effective_date": ev["effective_date"],
                    "group_code": group_code,
                    "control_number": control_number,
                }
            )
            sent += 1
        except Exception:
            # Already logged by a concurrent/retried call -- not a second send.
            continue
    return sent
