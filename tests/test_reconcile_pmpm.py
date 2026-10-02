from src.seed_mongo import get_client, seed, BUGGY_CLIENT_GROUP_CODE
from src.reconcile_pmpm import pmpm_naive, pmpm


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


def test_fixed_pmpm_resolves_the_misidentified_client():
    db = _seeded_db()
    naive_results = pmpm_naive(db)
    fixed_results = pmpm(db)

    buggy_fixed = fixed_results[BUGGY_CLIENT_GROUP_CODE]
    assert buggy_fixed["enrolled"] > 0
    assert buggy_fixed["pmpm"] is not None

    # every other client's figures are unchanged by the fix (same identity
    # resolution, just no longer silently failing for one client)
    for gc, naive_row in naive_results.items():
        if gc == BUGGY_CLIENT_GROUP_CODE:
            continue
        assert fixed_results[gc]["enrolled"] == naive_row["enrolled"]
        assert fixed_results[gc]["paid"] == naive_row["paid"]
