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
