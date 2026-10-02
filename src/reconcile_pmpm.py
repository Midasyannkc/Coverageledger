"""
Compute PMPM (per-member-per-month) rollups and census (enrolled headcount)
per client from claims and enrollment_events -- the JD's "PMPM/PEPM
rollups" and "census" reporting requirements plus its "reconciliation
mindset" requirement in one report.

PMPM = total paid claims / member-months observed (one claims row per
enrolled member per month, by construction -- see
data/synthetic/GENERATION_NOTES.md), which is independent of the
enrollment-headcount join bug below. Enrolled headcount (census) comes
from enrollment_events and IS affected by that bug, since census reporting
is exactly where a silently-dropped client would be caught.
"""
from collections import defaultdict


def _claims_by_group(db):
    paid = defaultdict(float)
    member_months = defaultdict(int)
    for c in db.claims.find():
        paid[c["group_code"]] += c["paid_amount"]
        member_months[c["group_code"]] += 1
    return paid, member_months


def pmpm_naive(db):
    """Naive join: enrollment_events.group_code straight against clients.group_code."""
    claims_paid, member_months = _claims_by_group(db)
    results = {}
    for client in db.clients.find():
        gc = client["group_code"]
        n_enrolled = db.enrollment_events.count_documents({"group_code": gc, "event_type": "add"})
        paid = claims_paid.get(gc, 0.0)
        mm = member_months.get(gc, 0)
        pmpm_value = (paid / mm) if mm else None
        results[gc] = {
            "paid": round(paid, 2),
            "enrolled": n_enrolled,
            "member_months": mm,
            "pmpm": round(pmpm_value, 2) if pmpm_value else None,
        }
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
    claims_paid, member_months = _claims_by_group(db)
    results = {}
    for client in db.clients.find():
        gc = client["group_code"]
        n_enrolled = db.enrollment_events.count_documents(
            {"group_code": {"$in": [gc, client["ein"]]}, "event_type": "add"}
        )
        paid = claims_paid.get(gc, 0.0)
        mm = member_months.get(gc, 0)
        pmpm_value = (paid / mm) if mm else None
        results[gc] = {
            "paid": round(paid, 2),
            "enrolled": n_enrolled,
            "member_months": mm,
            "pmpm": round(pmpm_value, 2) if pmpm_value else None,
        }
    return results
