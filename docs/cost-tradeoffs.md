# Cost & Architecture Trade-offs

## Storage: MongoDB (mongomock here) vs. a relational TPA core

TPA document estates (clients, members, enrollment events, claims) vary
shape client-to-client -- one client's plan design adds fields a dozen
others don't have. A document store lets onboarding a new client's feed
shape extend the schema without a migration, at the cost of needing the
governed semantic layer (`src/semantic_layer.py`) to do in application code
what a relational schema would otherwise enforce at the database level.
This sandbox cannot reach a real `mongod` binary (`fastdl.mongodb.org` is
blocked -- see `data/bronze/SOURCE.md`), so `mongomock` stands in; the
application code is written against the real `pymongo` client API and is
unchanged against a real cluster.

**Production sizing:** a mid-size TPA (dozens of clients, tens of
thousands of members) fits comfortably on a single MongoDB Atlas M30-M40
replica set (~$500-1,500/mo) with point-in-time backups, well short of
sharding.

## Orchestration: Lambda vs. always-on compute

834 generation and transmission is bursty (driven by enrollment events,
not a constant stream), which is the classic Lambda-shaped workload: a
few seconds of real work per invocation, long idle stretches between
them. The alternative -- an always-on ECS service polling for work -- pays
for idle capacity around the clock for no benefit, since nothing here
needs sub-second latency or a long-lived connection. The trade-off Lambda
accepts is a 15-minute max execution time and cold-start latency on the
first invocation after idle, both acceptable for a daily/event-driven
enrollment feed.

**Production sizing:** at a few hundred 834 transmissions/day, Lambda
invocation + S3 PUT costs stay in the free tier or low single-digit
dollars/month -- the ledger lookups against MongoDB dominate cost, not
compute.

## Scheduling: EventBridge + Step Functions vs. a cron box

A single Lambda invocation handles one orchestration pass; a real
deployment needs something to (a) trigger it on a schedule or event and
(b) sequence it with the downstream acknowledgment-reconciliation and
alerting steps this report's "transmission ledger" is designed to feed.
EventBridge (scheduled rule or an S3/SQS event trigger) and Step Functions
(sequencing + retry/backoff policy, replacing the hand-rolled
`simulate_timeout_once` retry test here) are the natural production
layer, and neither changes `lambda_orchestrator.py`'s code -- they just
decide when and how it's invoked. A traditional cron box would require
managing an EC2 instance, patching, and its own retry logic by hand for
no added capability.

## BI layer: Tableau/QuickSight vs. static charts

The JD names Tableau and QuickSight explicitly; neither SaaS product is
reachable from this sandbox. The charts in `docs/dashboard/` are rendered
directly from the same MongoDB queries (`src/render_dashboard_charts.py`)
that `reconcile_pmpm.py` exposes, so the only thing a real deployment
changes is the rendering layer -- pointing Tableau or QuickSight at the
same MongoDB collections (via the MongoDB BI Connector or a nightly
extract to S3/Athena for QuickSight) rather than at matplotlib. The
reconciliation logic, the identifier-normalization fix, and the
governed field definitions all live below the BI layer and are unaffected
by which tool renders them.

## RAG grounding: local TF-IDF/SVD vs. a hosted embedding model

`src/rag_index.py` embeds the governed semantic layer and the real X12
834 spec notes so an LLM-RAG layer answering "what does maintenance code
024 mean" or "what's the join key between clients and enrollment_events"
is grounded in the actual schema and spec rather than a model's prior
knowledge. `huggingface.co` (Chroma's default embedding backend) is
blocked in this sandbox, so a local TF-IDF + TruncatedSVD embedding
function (`LocalTfidfEmbeddingFunction`) stands in. In production, this
would be a hosted embedding model (Bedrock Titan Embeddings or OpenAI's
embedding API) behind the same Chroma (or OpenSearch/pgvector) interface
-- the governed semantic layer as the retrieval corpus, which is the part
that actually prevents the RAG layer from drifting out of sync with the
real schema, is unchanged either way.
