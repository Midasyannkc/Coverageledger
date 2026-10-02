import pytest

from src.seed_mongo import get_client, seed
from src.transmit_834 import transmit_naive, transmit


def _db_with_terminations():
    client = get_client()
    db = client["coverageledger"]
    seed(db)
    # find a client with at least one termination event
    for c in db.clients.find():
        n_term = db.enrollment_events.count_documents(
            {"event_type": "terminate", "group_code": {"$in": [c["group_code"], c["ein"]]}}
        )
        if n_term > 0:
            return db, c["group_code"], n_term
    raise RuntimeError("no client with terminations found in seed data")


def test_naive_transmitter_resends_termination_after_timeout_retry():
    db, group_code, n_term = _db_with_terminations()

    # First attempt: simulated timeout AFTER the ledger write already landed.
    with pytest.raises(TimeoutError):
        transmit_naive(db, group_code, control_number=1, simulate_timeout_once=True)

    ledger_after_timeout = db.transmission_ledger.count_documents({"group_code": group_code})
    assert ledger_after_timeout == n_term  # the "failed" call still wrote the ledger

    # Caller sees the TimeoutError and retries -- naive transmitter has no
    # idempotency check, so it logs the SAME terminations again.
    transmit_naive(db, group_code, control_number=2)

    ledger_after_retry = db.transmission_ledger.count_documents({"group_code": group_code})
    assert ledger_after_retry == n_term * 2  # BUG: every termination logged twice


def test_fixed_transmitter_sends_each_termination_exactly_once():
    db, group_code, n_term = _db_with_terminations()

    first = transmit(db, group_code, control_number=1)
    assert first == n_term

    # Retry (simulating a caller that didn't see the first call's result
    # and retries defensively) -- must be a no-op.
    second = transmit(db, group_code, control_number=2)
    assert second == 0

    ledger_count = db.transmission_ledger.count_documents({"group_code": group_code, "event_type": "terminate"})
    assert ledger_count == n_term  # exactly once, regardless of retries
