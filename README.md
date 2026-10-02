# CoverageLedger

A TPA (third-party administrator) enrollment, transmission-reconciliation,
and LLM-RAG analytics platform, built for Nonstop Health's Senior Data
Engineer posting -- which asks for X12 834 enrollment transaction
handling, a transmission ledger with exactly-once guarantees, identifier
normalization across EIN/group-code/member-ID systems, AWS serverless
orchestration, PMPM/PEPM and census reporting, and an LLM-RAG layer
grounded in a governed semantic layer.

## What this is

- **Real spec anchor:** the DC Health Benefit Exchange's own X12 834
  (Benefit Enrollment and Maintenance) Companion Guide, a real public
  carrier enrollment spec -- segment layout (ISA/GS/ST/BGN/N1/INS/REF/DTP/SE/GE/IEA)
  and maintenance-type codes (021 = Addition, 024 = Cancellation/Termination)
  are taken directly from it, not invented (see `data/bronze/SOURCE.md`
  for exact provenance).
- **Disclosed-synthetic TPA estate:** 6 employer-group clients, 274
  members, 321 enrollment events, and 1,674 claims, seeded into a
  MongoDB-API-compatible store (`mongomock`, since this sandbox cannot
  reach a real `mongod` -- see `data/bronze/SOURCE.md`), internally
  consistent rather than arbitrary (see `data/synthetic/GENERATION_NOTES.md`).
- **Two real incidents**, each reproduced and fixed with genuine git
  history (see `docs/incidents.md` for the full detail):
  1. A naive retry-on-timeout transmitter re-sent an already-logged
     termination after a simulated SFTP timeout, doubling the ledger.
     Fixed with a unique natural-key index and an already-sent check, so
     a retry after success is a verified no-op.
  2. A legacy enrollment loader wrote one client's EIN into the
     `group_code` field instead of its real group code, silently
     zeroing that client's reported census on a naive join while its
     claims-derived PMPM looked unaffected -- exactly the kind of
     cross-report inconsistency a reconciliation mindset exists to catch.
     Fixed by resolving enrollment events against either identifier.
- **PMPM and census rollups** (`src/reconcile_pmpm.py`), corrected mid-build
  from an initial headcount-denominator mistake (unrealistic
  $4,700-$5,381/month figures) to a claims-derived member-months
  denominator (realistic $777-$858/month figures) -- see `AI_DEV_LOG.md`.
- **A real AWS Lambda orchestrator** generating and uploading 834 files to
  S3, verified against `moto`-mocked S3 (`src/lambda_orchestrator.py`).
- **A governed semantic layer** (`src/semantic_layer.py`) -- field
  definitions, business rules, and join keys as a single versioned
  source, consumed by both the reconciliation report and the RAG index so
  they can't silently drift.
- **An LLM-RAG grounding layer** (`src/rag_index.py`) answering natural-
  language questions (e.g. "what does maintenance code 024 mean?", "what's
  the join key between clients and enrollment_events?") against the
  governed semantic layer and the real X12 834 spec, using a local
  TF-IDF+SVD embedding function since `huggingface.co` is blocked in this
  sandbox.
- **A Tableau/QuickSight-equivalent dashboard** (static charts, since
  neither SaaS product is reachable from this sandbox -- see
  `docs/dashboard/`).

## Repository layout

```
data/
  bronze/        real X12 834 spec source documentation
  synthetic/     disclosed-synthetic TPA estate generation notes
docs/
  x12_834_spec_notes.md   real segment/code spec extracted from the
                           companion guide
  incidents.md            full incident reports with git log excerpts
  architecture.md          pipeline diagram
  cost-tradeoffs.md        sandbox-constraint disclosures and production targets
  dashboard/               rendered charts (PMPM, enrollment lifecycle,
                            exactly-once transmission)
src/
  seed_mongo.py            synthetic TPA estate seeder (mongomock)
  x12_834_generator.py     real X12 834 generator + reverse-parser
  transmit_834.py          naive (Incident 1) + fixed transmitter
  reconcile_pmpm.py        naive (Incident 2) + fixed PMPM/census reconciler
  lambda_orchestrator.py   AWS Lambda handler, moto-mocked S3
  semantic_layer.py        governed field defs/business rules/join keys
  rag_index.py             Chroma + local TF-IDF/SVD RAG grounding
  render_dashboard_charts.py  dashboard renderer
tests/            pytest suite, 12/12 passing
AI_DEV_LOG.md     what was AI-assisted vs. human-directed/validated
CODING_STANDARDS.md
CoverageLedger_Executive_Summary.pptx
```

## Running it

```
pip install -r requirements.txt
python -m pytest tests/ -v                    # 12/12
python -m src.seed_mongo                      # seed the synthetic TPA estate
python -m src.render_dashboard_charts         # dashboard PNGs (also exercises
                                               # the transmitter and reconciler)
```

## Known, disclosed scope limits

- MongoDB itself is not reachable from this sandbox (`fastdl.mongodb.org`
  is blocked); `mongomock` stands in, written against the real `pymongo`
  client API, so the application code is unchanged against a real cluster
  (see `data/bronze/SOURCE.md`).
- The TPA client/member/claims estate is disclosed-synthetic, generated to
  be internally consistent (member-months per claims row, realistic PMPM
  ranges) rather than arbitrary (see `data/synthetic/GENERATION_NOTES.md`).
- Tableau and Amazon QuickSight are not reachable from this sandbox; the
  dashboard renders as static charts from the same underlying queries
  (see `docs/cost-tradeoffs.md`).
- `huggingface.co` (Chroma's default embedding backend) is blocked; a
  local TF-IDF+SVD embedding function stands in for a hosted embedding
  model (see `docs/cost-tradeoffs.md`).
- EventBridge/Step Functions scheduling around the Lambda handler is
  documented, not deployed, since no real AWS account is reachable from
  this sandbox either (see `docs/cost-tradeoffs.md`).
