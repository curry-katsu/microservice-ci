from typing import Any

import boto3


class SqsClient:
    def __init__(
        self, client: Any | None = None, region_name: str | None = None
    ) -> None:
        self._client = client or boto3.client("sqs", region_name=region_name)

    def send_message(
        self,
        queue_url: str,
        message_body: str,
        message_attributes: dict[str, Any] | None = None,
        delay_seconds: int | None = None,
    ) -> str:
        params: dict[str, Any] = {
            "QueueUrl": queue_url,
            "MessageBody": message_body,
        }
        if message_attributes:
            params["MessageAttributes"] = message_attributes
        if delay_seconds is not None:
            params["DelaySeconds"] = delay_seconds

        response = self._client.send_message(**params)
        return str(response["MessageId"])
