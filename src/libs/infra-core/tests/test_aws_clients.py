from typing import Any

from infra_core.aws.dynamodb import DynamoDbClient
from infra_core.aws.s3 import S3Client
from infra_core.aws.sns import SnsClient
from infra_core.aws.sqs import SqsClient


class FakeTable:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def put_item(self, **params: Any) -> dict[str, Any]:
        self.calls.append(("put_item", params))
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def get_item(self, **params: Any) -> dict[str, Any]:
        self.calls.append(("get_item", params))
        return {"Item": {"id": "item-1", "value": "stored"}}

    def update_item(self, **params: Any) -> dict[str, Any]:
        self.calls.append(("update_item", params))
        return {"Attributes": {"id": "item-1", "value": "updated"}}

    def delete_item(self, **params: Any) -> dict[str, Any]:
        self.calls.append(("delete_item", params))
        return {"Attributes": {"id": "item-1"}}

    def query(self, **params: Any) -> dict[str, Any]:
        self.calls.append(("query", params))
        return {"Items": [{"id": "item-1"}]}

    def scan(self, **params: Any) -> dict[str, Any]:
        self.calls.append(("scan", params))
        return {"Items": [{"id": "item-1"}]}

    def batch_writer(self) -> "FakeBatchWriter":
        return FakeBatchWriter(self)


class FakeBatchWriter:
    def __init__(self, table: FakeTable) -> None:
        self._table = table

    def __enter__(self) -> "FakeBatchWriter":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def put_item(self, **params: Any) -> None:
        self._table.calls.append(("batch_put_item", params))


class FakeDynamoResource:
    def __init__(self, table: FakeTable) -> None:
        self.table = table

    def Table(self, table_name: str) -> FakeTable:
        self.table.calls.append(("Table", {"table_name": table_name}))
        return self.table


class FakeAwsClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def put_object(self, **params: Any) -> dict[str, Any]:
        self.calls.append(params)
        return self.response

    def publish(self, **params: Any) -> dict[str, Any]:
        self.calls.append(params)
        return self.response

    def send_message(self, **params: Any) -> dict[str, Any]:
        self.calls.append(params)
        return self.response


def test_dynamodb_client_wraps_table_operations() -> None:
    table = FakeTable()
    client = DynamoDbClient(resource=FakeDynamoResource(table))

    assert client.put_item("events", {"id": "item-1"})["ResponseMetadata"]
    assert client.get_item("events", {"id": "item-1"}, consistent_read=True) == {
        "id": "item-1",
        "value": "stored",
    }
    assert client.update_item(
        "events",
        {"id": "item-1"},
        "SET #value = :value",
        expression_attribute_values={":value": "updated"},
        expression_attribute_names={"#value": "value"},
    )["Attributes"] == {"id": "item-1", "value": "updated"}
    assert client.delete_item("events", {"id": "item-1"})["Attributes"] == {
        "id": "item-1"
    }
    assert client.query("events", "id = :id") == [{"id": "item-1"}]
    assert client.scan("events") == [{"id": "item-1"}]

    client.batch_write_items("events", [{"id": "item-2"}, {"id": "item-3"}])

    assert ("batch_put_item", {"Item": {"id": "item-2"}}) in table.calls
    assert ("batch_put_item", {"Item": {"id": "item-3"}}) in table.calls


def test_s3_client_returns_etag_and_passes_content_type() -> None:
    fake_client = FakeAwsClient({"ETag": '"etag-1"'})
    client = S3Client(client=fake_client)

    etag = client.put_object("bucket", "key", b"body", content_type="text/plain")

    assert etag == '"etag-1"'
    assert fake_client.calls == [
        {
            "Bucket": "bucket",
            "Key": "key",
            "Body": b"body",
            "ContentType": "text/plain",
        }
    ]


def test_sns_client_returns_message_id() -> None:
    fake_client = FakeAwsClient({"MessageId": "message-1"})
    client = SnsClient(client=fake_client)

    message_id = client.publish("topic-arn", "hello", subject="subject")

    assert message_id == "message-1"
    assert fake_client.calls == [
        {"TopicArn": "topic-arn", "Message": "hello", "Subject": "subject"}
    ]


def test_sqs_client_returns_message_id() -> None:
    fake_client = FakeAwsClient({"MessageId": "message-1"})
    client = SqsClient(client=fake_client)

    message_id = client.send_message("queue-url", "hello", delay_seconds=3)

    assert message_id == "message-1"
    assert fake_client.calls == [
        {"QueueUrl": "queue-url", "MessageBody": "hello", "DelaySeconds": 3}
    ]
