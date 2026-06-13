from typing import Any

import boto3


class SnsClient:
    def __init__(
        self, client: Any | None = None, region_name: str | None = None
    ) -> None:
        self._client = client or boto3.client("sns", region_name=region_name)

    def publish(
        self,
        topic_arn: str,
        message: str,
        subject: str | None = None,
        message_attributes: dict[str, Any] | None = None,
    ) -> str:
        params: dict[str, Any] = {
            "TopicArn": topic_arn,
            "Message": message,
        }
        if subject:
            params["Subject"] = subject
        if message_attributes:
            params["MessageAttributes"] = message_attributes

        response = self._client.publish(**params)
        return str(response["MessageId"])
