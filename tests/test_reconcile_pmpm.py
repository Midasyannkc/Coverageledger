from src.seed_mongo import get_client, seed, BUGGY_CLIENT_GROUP_CODE
from src.reconcile_pmpm import pmpm_naive


def _seeded_db():
    client = get_client()
    db = client["coverageledger"]
    seed(db)
    return db


def test_naive_pmpm_silently_zeroes_out_the_misidentified_client():
    db = _seeded_db()
    results = pmpm_naive(db)
    buggy = results[BUGGY_CLIENT_GROUP_CODE]
    # BUG: the legacy loader wrote this client's enrollment_events under its
    # EIN instead of its group_code, so a naive group_code join finds ZERO
    # enrolled members for a client that has real claims paid -- and the
    # report does not error, it just silently reports an undefined PMPM.
    assert buggy["enrolled"] == 0
    assert buggy["paid"] > 0
    assert buggy["pmpm"] is None

    # every other client resolves fine
    others = [v for k, v in results.items() if k != BUGGY_CLIENT_GROUP_CODE]
    assert all(o["enrolled"] > 0 for o in others)
