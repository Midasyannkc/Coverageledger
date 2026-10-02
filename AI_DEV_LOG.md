# AI Development Log

This project was built with Claude Code as an AI-assisted development tool.
This log discloses what was AI-assisted versus human-directed and
validated, rather than presenting the result as either fully automated or
fully manual.

| Area | AI-assisted | Human-directed / validated |
|---|---|---|
| Real spec sourcing | Extracted the X12 834 segment layout and maintenance-type codes from the DC HBX companion guide PDF once direct carrier-spec downloads were confirmed blocked | Confirmed the extracted segment structure (ISA/GS/ST/BGN/N1/INS/REF/DTP/SE/GE/IEA) matches the real X12 834 transaction set before coding against it; decision to disclose the MongoDB sandbox constraint (no reachable `mongod`) rather than silently fake a connection |
| Synthetic TPA estate | Wrote the `mongomock` seeding code and the client/member/enrollment/claims generators | Chose which client's enrollment events would carry the identifier bug (`BUGGY_CLIENT_GROUP_CODE`) and why, so the reconciliation incident models a real legacy-loader failure mode rather than an arbitrary injected error |
| 834 generation/transmission | Wrote the generator and the naive/fixed transmitter implementations | Confirmed round-trip correctness (generated segments re-parse to the same maintenance codes and dates) before trusting the generator; chose the natural key (`member_id`, `event_type`, `effective_date`) the idempotency fix is built on |
| PMPM reconciliation | Wrote the naive and fixed join logic | Caught and corrected a real methodological error mid-build: the first "fixed" PMPM used enrollment headcount as the denominator, producing unrealistic $4,700-$5,381/month figures; re-derived PMPM from claims-based member-months instead, producing realistic $777-$858 figures, and updated the test suite's assertions to match the corrected (still bug-exposing) behavior |
| RAG grounding | Wrote the Chroma index code and the local TF-IDF/SVD embedding function (standing in for a `huggingface.co`-hosted model blocked in this sandbox) | Chose what belongs in the governed semantic layer that both the reconciliation report and the RAG index consume, so the two can't silently drift from each other |
| Dashboard | Wrote the chart code following this portfolio's established color/style conventions | Reviewed each rendered chart (including the corrected PMPM figures) before committing |
| Documentation | Drafted README/incident-report prose | Verified every number quoted in the docs against a live rerun of the pipeline before publishing |

**What this demonstrates for the role:** AI tools accelerated the
mechanical parts (writing the generator/transmitter, seeding synthetic
data, drafting docs), while the judgment calls this JD actually tests
for -- catching a methodologically wrong PMPM calculation before shipping
it, choosing a realistic identifier-mismatch failure mode to model, and
disclosing sandbox constraints (MongoDB, Tableau/QuickSight,
huggingface.co) honestly rather than faking them -- stayed
human-directed throughout.
