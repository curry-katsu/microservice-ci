import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError


def create_aws_client(
    service_name: str,
    *,
    endpoint_url: str | None = None,
    region_name: str | None = None,
) -> Any:
    normalized_service = service_name.upper().replace("-", "_")
    region = region_name or os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
    return boto3.client(
        service_name,
        endpoint_url=(
            endpoint_url
            or os.getenv(f"AWS_ENDPOINT_URL_{normalized_service}")
            or os.getenv("AWS_ENDPOINT_URL")
            or "http://localhost:4566"
        ),
        region_name=region,
    )


def ensure_s3_bucket(
    client: Any,
    bucket: str,
    *,
    region_name: str | None = None,
) -> None:
    try:
        client.head_bucket(Bucket=bucket)
        return
    except ClientError as error:
        status_code = int(
            error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        )
        if status_code not in {403, 404}:
            raise

    region = region_name or os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
    if region == "us-east-1":
        client.create_bucket(Bucket=bucket)
        return

    client.create_bucket(
        Bucket=bucket,
        CreateBucketConfiguration={"LocationConstraint": region},
    )


def delete_s3_prefix(client: Any, bucket: str, prefix: str) -> None:
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if objects:
            client.delete_objects(Bucket=bucket, Delete={"Objects": objects})


def read_s3_text(client: Any, bucket: str, key: str) -> str:
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    text = body.decode("utf-8")
    return str(text)


def read_s3_json(client: Any, bucket: str, key: str) -> Any:
    return json.loads(read_s3_text(client, bucket, key))
