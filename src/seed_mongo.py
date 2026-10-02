"""
Seed a disclosed-synthetic TPA MongoDB document estate (via mongomock,
since no real mongod is reachable from this sandbox -- see
data/bronze/SOURCE.md) with the collections Nonstop Health's own posting
names: clients, members, enrollment_events, claims.

Deliberately injects two realistic data-quality problems for Incidents 1
and 2 (see docs/incidents.md) rather than narrating them after the fact:
  - Incident 1's trigger lives in src/transmit_834.py (a retried
    transmission), not here.
  - Incident 2's trigger is injected here: one client's enrollment_events
    were loaded by a legacy process that wrote the EIN into the
    group_code field instead of the real group code.
"""
import random
from datetime import date, datetime, timedelta

import mongomock


def _dt(d: date) -> datetime:
    """BSON has no date type, only datetime -- store at midnight UTC."""
    return datetime(d.year, d.month, d.day)

RANDOM_SEED = 20240601

CLIENTS = [
    {"group_code": "GRP-01", "name": "Lakeshore Logistics", "ein": "741234561", "funding_type": "self-funded"},
    {"group_code": "GRP-02", "name": "Brightline Dental Partners", "ein": "741234562", "funding_type": "level-funded"},
    {"group_code": "GRP-03", "name": "Parkview Manufacturing", "ein": "741234563", "funding_type": "self-funded"},
    {"group_code": "GRP-04", "name": "Summit Retail Group", "ein": "741234564", "funding_type": "level-funded"},
    {"group_code": "GRP-05", "name": "Cedar Health Collective", "ein": "741234565", "funding_type": "self-funded"},
    {"group_code": "GRP-06", "name": "Northgate Financial", "ein": "741234566", "funding_type": "level-funded"},
]

# INCIDENT 2 trigger: this client's enrollment events were loaded by a
# legacy process that wrote EIN into the group_code field.
BUGGY_CLIENT_GROUP_CODE = "GRP-04"


def get_client():
    """Return a fresh mongomock client (mirrors pymongo.MongoClient's API)."""
    return mongomock.MongoClient()


def seed(db):
    rng = random.Random(RANDOM_SEED)

    db.clients.insert_many(CLIENTS)

    members = []
    enrollment_events = []
    claims = []
    member_counter = 1

    for client in CLIENTS:
        n_members = rng.randint(30, 55)
        for _ in range(n_members):
            member_id = f"MBR-{member_counter:05d}"
            member_counter += 1
            is_subscriber = rng.random() < 0.65
            hire_date = date(2024, rng.randint(1, 6), rng.randint(1, 28))

            members.append(
                {
                    "member_id": member_id,
                    "subscriber_id": member_id if is_subscriber else f"MBR-{member_counter - 2:05d}",
                    "group_code": client["group_code"],
                    "relationship_code": "subscriber" if is_subscriber else "dependent",
                }
            )

            # Enrollment add event
            logged_group_code = (
                client["ein"] if client["group_code"] == BUGGY_CLIENT_GROUP_CODE else client["group_code"]
            )
            enrollment_events.append(
                {
                    "member_id": member_id,
                    "group_code": logged_group_code,
                    "event_type": "add",
                    "maintenance_type_code": "021",
                    "effective_date": _dt(hire_date),
                }
            )

            # Some members terminate later in the year
            if rng.random() < 0.18:
                term_date = hire_date + timedelta(days=rng.randint(60, 200))
                enrollment_events.append(
                    {
                        "member_id": member_id,
                        "group_code": logged_group_code,
                        "event_type": "terminate",
                        "maintenance_type_code": "024",
                        "effective_date": _dt(term_date),
                        "transmitted": False,
                    }
                )

            # Monthly claims while enrolled (simplified: 3-9 months of claims)
            n_months = rng.randint(3, 9)
            for m in range(n_months):
                service_month = date(2024, min(12, hire_date.month + m), 1)
                allowed = round(rng.uniform(50, 1800), 2)
                paid = round(allowed * rng.uniform(0.75, 0.95), 2)
                claims.append(
                    {
                        "member_id": member_id,
                        "group_code": client["group_code"],  # claims loader is NOT affected by the bug
                        "service_month": _dt(service_month),
                        "allowed_amount": allowed,
                        "paid_amount": paid,
                    }
                )

    db.members.insert_many(members)
    db.enrollment_events.insert_many(enrollment_events)
    db.claims.insert_many(claims)
    return {
        "clients": len(CLIENTS),
        "members": len(members),
        "enrollment_events": len(enrollment_events),
        "claims": len(claims),
    }


if __name__ == "__main__":
    client = get_client()
    db = client["coverageledger"]
    counts = seed(db)
    print(counts)
