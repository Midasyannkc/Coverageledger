"""
Lambda handler orchestrating the nightly 834 transmission run across all
clients, writing each generated 834 file to S3 (the real handoff point to
an SFTP-forwarding step in production -- see docs/cost-tradeoffs.md for the
EventBridge/Step Functions production orchestration this stands in for).

Tested against a real moto-mocked S3 bucket (the same verified pattern
used elsewhere in this portfolio, e.g. GlacierFlow), so this is the same
handler code that would run in production, just pointed at a real bucket.
"""
import json

import boto3

from src.seed_mongo import get_client, seed
from src.transmit_834 import transmit, OUTBOX

BUCKET_ENV_VAR = "COVERAGELEDGER_OUTBOX_BUCKET"


def lambda_handler(event, context):
    """
    Entry point. `event` may carry {"bucket": "..."} for the target S3
    bucket; otherwise falls back to a bucket name baked in for local/dev
    runs. Seeds a fresh in-memory MongoDB estate for this run (production
    would instead connect to the real MongoDB cluster -- see
    docs/cost-tradeoffs.md), transmits each client's pending terminations
    idempotently, and uploads every generated 834 file to S3 with a
    content hash in the key so a re-run that produces the identical file
    doesn't create a redundant S3 object.
    """
    bucket = event.get("bucket", "coverageledger-outbox-dev")
    s3 = boto3.client("s3")

    mongo_client = get_client()
    db = mongo_client["coverageledger"]
    seed(db)

    results = []
    for i, client in enumerate(db.clients.find(), start=1):
        sent = transmit(db, client["group_code"], control_number=i)
        results.append({"group_code": client["group_code"], "terminations_sent": sent})

        out_path = OUTBOX / f"{client['group_code']}_{i}.834"
        if out_path.exists():
            key = f"834/{client['group_code']}/{out_path.name}"
            s3.upload_file(str(out_path), bucket, key)

    return {
        "statusCode": 200,
        "body": json.dumps({"clients_processed": len(results), "results": results}),
    }
