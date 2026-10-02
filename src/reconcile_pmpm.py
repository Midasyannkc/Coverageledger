"""
Compute PMPM (per-member-per-month) rollups per client from claims,
reconciled against the enrolled member count from enrollment_events --
the JD's "PMPM/PEPM rollups" reporting requirement plus its "reconciliation
mindset" requirement in one report.
"""
from collections import defaultdict


def _claims_paid_by_group(db):
    totals = defaultdict(float)
    for c in db.claims.find():
        totals[c["group_code"]] += c["paid_amount"]
    return totals


def pmpm_naive(db):
    """Naive join: enrollment_events.group_code straight against clients.group_code."""
    claims_paid = _claims_paid_by_group(db)
    results = {}
    for client in db.clients.find():
        gc = client["group_code"]
        n_enrolled = db.enrollment_events.count_documents({"group_code": gc, "event_type": "add"})
        paid = claims_paid.get(gc, 0.0)
        pmpm = (paid / n_enrolled) if n_enrolled else None
        results[gc] = {"paid": round(paid, 2), "enrolled": n_enrolled, "pmpm": round(pmpm, 2) if pmpm else None}
    return results


def pmpm(db):
    """
    FIX: resolve enrollment_events to their real client by matching on
    EITHER group_code OR ein (one legacy-loaded client's events are keyed
    by ein instead of group_code), via an explicit identifier-
    normalization step built from the clients collection -- the JD's
    "normalize across the many identifier systems" requirement applied
    directly, rather than assuming a single foreign key always matches.
    """
    claims_paid = _claims_paid_by_group(db)
    results = {}
    for client in db.clients.find():
        gc = client["group_code"]
        n_enrolled = db.enrollment_events.count_documents(
            {"group_code": {"$in": [gc, client["ein"]]}, "event_type": "add"}
        )
        paid = claims_paid.get(gc, 0.0)
        pmpm_value = (paid / n_enrolled) if n_enrolled else None
        results[gc] = {
            "paid": round(paid, 2),
            "enrolled": n_enrolled,
            "pmpm": round(pmpm_value, 2) if pmpm_value else None,
        }
    return results
