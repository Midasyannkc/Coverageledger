# Synthetic Data: Generation Notes (disclosed)

No real TPA member/claims data is public (correctly -- it's PHI). The
MongoDB document estate in `src/seed_mongo.py` is disclosed-synthetic,
generated to mirror the collection structure Nonstop Health's own posting
names explicitly: clients, members, enrollments, claims, cards, reserves.

- **Clients**: 6 synthetic self-funded/level-funded employer groups, each
  with a `group_code` and `ein` (randomly generated, not real EINs).
- **Members**: 250 synthetic members across those clients, each with a
  `member_id`, `subscriber_id`, relationship code (subscriber/dependent),
  and a `group_code` foreign key.
- **Enrollment events**: an add/change/terminate lifecycle per member,
  generated with realistic timing (hire-date add, occasional mid-year plan
  changes, a minority terminated), matching the real INS03 maintenance-type
  codes documented in `docs/x12_834_spec_notes.md`.
- **Claims**: synthetic monthly claims per enrolled member, with a
  plan-level allowed/paid amount split, used to compute PMPM (per-member-
  per-month) rollups.
- **Random seed**: fixed (`RANDOM_SEED = 20240601` in `src/seed_mongo.py`)
  for reproducibility.

Deliberately includes two realistic data-quality problems, reproduced and
fixed with genuine git history (see `docs/incidents.md`):
1. A retried termination transmission (the same member terminated twice due
   to a naive retry-on-timeout policy).
2. A client identifier mismatch between the MongoDB `clients` collection
   (which stores `group_code`) and the enrollment ledger (which a legacy
   loader populated with `EIN` instead for one client), breaking a
   downstream join.
