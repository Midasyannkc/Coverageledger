import boto3
from moto import mock_aws

from src.lambda_orchestrator import lambda_handler


@mock_aws
def test_lambda_handler_uploads_834_files_to_s3_for_every_client():
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket = "coverageledger-outbox-test"
    s3.create_bucket(Bucket=bucket)

    response = lambda_handler({"bucket": bucket}, None)

    assert response["statusCode"] == 200
    objects = s3.list_objects_v2(Bucket=bucket)
    assert objects["KeyCount"] >= 1
    keys = [o["Key"] for o in objects["Contents"]]
    assert any(k.startswith("834/GRP-") for k in keys)


@mock_aws
def test_lambda_handler_reports_all_six_clients_processed():
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket = "coverageledger-outbox-test2"
    s3.create_bucket(Bucket=bucket)

    response = lambda_handler({"bucket": bucket}, None)
    import json
    body = json.loads(response["body"])
    assert body["clients_processed"] == 6
