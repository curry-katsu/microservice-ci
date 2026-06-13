from typing import Any

import boto3


class S3Client:
    def __init__(
        self, client: Any | None = None, region_name: str | None = None
    ) -> None:
        self._client = client or boto3.client("s3", region_name=region_name)

    def put_object(
        self,
        bucket: str,
        key: str,
        body: bytes | str,
        content_type: str | None = None,
    ) -> str:
        params: dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "Body": body,
        }
        if content_type:
            params["ContentType"] = content_type

        response = self._client.put_object(**params)
        return str(response["ETag"])
