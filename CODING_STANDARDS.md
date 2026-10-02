# Coding Standards & Review Guidelines

Followed throughout this repository's git history:

1. **One concern per module.** Generation (`x12_834_generator.py`),
   transmission (`transmit_834.py`), reconciliation (`reconcile_pmpm.py`),
   orchestration (`lambda_orchestrator.py`), and presentation
   (`render_dashboard_charts.py`, `rag_index.py`) are kept in separate
   files so a change to one doesn't require touching the others.
2. **Every data-shape assumption gets a pinned test.** The X12 834
   round-trip tests re-parse generated segments and assert against
   independently known maintenance codes and dates, not against the
   generator's own internal state.
3. **Fixes are proven, not asserted.** Every incident in
   `docs/incidents.md` has a before-state commit (bug reproduced, test
   failing) and a separate after-state commit (fix applied, test passing,
   figures reconciled) -- never a single commit claiming both.
4. **No silent fallbacks.** A missing or unreachable dependency (real
   `mongod`, a hosted embedding model, Tableau/QuickSight) is disclosed in
   the relevant `SOURCE.md` / `GENERATION_NOTES.md` / `cost-tradeoffs.md`,
   not quietly faked without a note.
5. **Idempotent by default.** `transmit()` guarantees exactly-once
   delivery via a unique natural-key index rather than assuming the
   caller never retries.
6. **Identifiers are normalized explicitly, never assumed.** `reconcile_pmpm.py`
   resolves enrollment events against both `group_code` and `ein` rather
   than trusting a single foreign key always matches -- the same
   discipline applied to every join in this codebase.
7. **A single governed semantic layer backs every consumer.** Field
   definitions, business rules, and join keys live once in
   `semantic_layer.py` and are read by both the reconciliation report and
   the RAG index, so they cannot silently drift apart.
8. **Commit messages state the verification, not just the change** -- e.g.
   "8/8 tests passing" or the exact reconciled PMPM figures -- so the git
   log itself is a verification trail.
