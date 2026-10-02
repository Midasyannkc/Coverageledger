# Architecture

```
REAL SPEC ANCHOR                           DISCLOSED SYNTHETIC
┌──────────────────────────┐               ┌───────────────────────────┐
│ DC HBX 834 Companion      │               │ TPA document estate:      │
│ Guide (real public carrier│               │ clients, members,         │
│ enrollment spec)          │               │ enrollment_events, claims │
└──────────┬────────────────┘               └──────────┬─────────────────┘
           │ segment layout, qualifier codes            │ mongomock (pymongo API)
           ▼                                            ▼
  src/x12_834_generator.py  <───── joined on member_id ─── MongoDB document estate
           │                                            │
           ▼                                            ▼
  src/transmit_834.py  (Incident 1 fix: idempotent,    src/reconcile_pmpm.py
   unique natural-key ledger)                           (Incident 2 fix: group_code
           │                                             OR ein identifier resolution)
           ▼                                            │
  data/outbox/*.834  ──upload──▶  S3 (moto-mocked)       ▼
           ▲                                    docs/dashboard/*.png
           │                                    (PMPM, census, exactly-once charts)
  src/lambda_orchestrator.py
  (Lambda handler, real moto-mocked S3)

  src/semantic_layer.py  ──indexed by──▶  src/rag_index.py
  (governed field defs,                   (Chroma + local TF-IDF/SVD embeddings,
   business rules, join keys)              grounds NL questions in the real spec
                                            and the governed schema)
```

## Storage

MongoDB document estate via `mongomock` (no real `mongod` reachable from
this sandbox -- see `data/bronze/SOURCE.md`), written against the real
`pymongo` client API, so the application code is identical to what would
run against a real MongoDB cluster.

## Orchestration

A real AWS Lambda handler (`src/lambda_orchestrator.py`), verified against
`moto`-mocked S3 (the same verified pattern as this portfolio's GlacierFlow
project). ECS Fargate / EventBridge / Step Functions are documented as the
production orchestration layer around this handler in
`docs/cost-tradeoffs.md`, since none of their AWS APIs change the handler
code itself -- EventBridge would simply invoke this same Lambda on a
schedule, and Step Functions would sequence it with downstream
acknowledgment-reconciliation and alerting steps.

## BI layer

Tableau and Amazon QuickSight (the JD's stated tools) are not reachable
from this sandbox, so the dashboard renders as static charts from the same
underlying MongoDB queries -- see `docs/dashboard/`.
