import pytest

from src.seed_mongo import get_client, seed
from src.transmit_834 import transmit_naive


def _db_with_terminations():
    client = get_client()
    db = client["coverageledger"]
    seed(db)
    for c in db.clients.find():
        n_term = db.enrollment_events.count_documents(
            {"event_type": "terminate", "group_code": {"$in": [c["group_code"], c["ein"]]}}
        )
        if n_term > 0:
            return db, c["group_code"], n_term
    raise RuntimeError("no client with terminations found in seed data")


def test_naive_transmitter_resends_termination_after_timeout_retry():
    db, group_code, n_term = _db_with_terminations()

    with pytest.raises(TimeoutError):
        transmit_naive(db, group_code, control_number=1, simulate_timeout_once=True)

    ledger_after_timeout = db.transmission_ledger.count_documents({"group_code": group_code})
    assert ledger_after_timeout == n_term  # the "failed" call still wrote the ledger

    # Caller sees the TimeoutError and retries -- naive transmitter has no
    # idempotency check, so it logs the SAME terminations again.
    transmit_naive(db, group_code, control_number=2)

    ledger_after_retry = db.transmission_ledger.count_documents({"group_code": group_code})
    assert ledger_after_retry == n_term * 2  # BUG: every termination logged twice
