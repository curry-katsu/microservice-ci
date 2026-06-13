from abc import ABC, abstractmethod
from typing import Any, cast

import boto3


class AbstractDynamoDbClient(ABC):
    @abstractmethod
    def put_item(self, table_name: str, item: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_item(
        self,
        table_name: str,
        key: dict[str, Any],
        consistent_read: bool | None = None,
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def update_item(
        self,
        table_name: str,
        key: dict[str, Any],
        update_expression: str,
        expression_attribute_values: dict[str, Any] | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        condition_expression: str | None = None,
        return_values: str = "ALL_NEW",
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        table_name: str,
        key_condition_expression: Any,
        expression_attribute_values: dict[str, Any] | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        index_name: str | None = None,
        filter_expression: Any | None = None,
        limit: int | None = None,
        scan_index_forward: bool | None = None,
        consistent_read: bool | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class DynamoDbClient(AbstractDynamoDbClient):
    def __init__(
        self,
        resource: Any | None = None,
        region_name: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self._resource = resource or boto3.resource(
            "dynamodb",
            region_name=region_name,
            endpoint_url=endpoint_url,
        )

    def put_item(self, table_name: str, item: dict[str, Any]) -> dict[str, Any]:
        table = self._resource.Table(table_name)
        return cast(dict[str, Any], table.put_item(Item=item))

    def get_item(
        self,
        table_name: str,
        key: dict[str, Any],
        consistent_read: bool | None = None,
    ) -> dict[str, Any] | None:
        table = self._resource.Table(table_name)
        params: dict[str, Any] = {"Key": key}
        if consistent_read is not None:
            params["ConsistentRead"] = consistent_read

        response = table.get_item(**params)
        item = response.get("Item")
        return item if isinstance(item, dict) else None

    def update_item(
        self,
        table_name: str,
        key: dict[str, Any],
        update_expression: str,
        expression_attribute_values: dict[str, Any] | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        condition_expression: str | None = None,
        return_values: str = "ALL_NEW",
    ) -> dict[str, Any]:
        table = self._resource.Table(table_name)
        params: dict[str, Any] = {
            "Key": key,
            "UpdateExpression": update_expression,
            "ReturnValues": return_values,
        }
        if expression_attribute_values:
            params["ExpressionAttributeValues"] = expression_attribute_values
        if expression_attribute_names:
            params["ExpressionAttributeNames"] = expression_attribute_names
        if condition_expression:
            params["ConditionExpression"] = condition_expression

        return cast(dict[str, Any], table.update_item(**params))

    def delete_item(
        self,
        table_name: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        return_values: str | None = None,
    ) -> dict[str, Any]:
        table = self._resource.Table(table_name)
        params: dict[str, Any] = {"Key": key}
        if condition_expression:
            params["ConditionExpression"] = condition_expression
        if expression_attribute_values:
            params["ExpressionAttributeValues"] = expression_attribute_values
        if expression_attribute_names:
            params["ExpressionAttributeNames"] = expression_attribute_names
        if return_values:
            params["ReturnValues"] = return_values

        return cast(dict[str, Any], table.delete_item(**params))

    def query(
        self,
        table_name: str,
        key_condition_expression: Any,
        expression_attribute_values: dict[str, Any] | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        index_name: str | None = None,
        filter_expression: Any | None = None,
        limit: int | None = None,
        scan_index_forward: bool | None = None,
        consistent_read: bool | None = None,
    ) -> list[dict[str, Any]]:
        table = self._resource.Table(table_name)
        params: dict[str, Any] = {
            "KeyConditionExpression": key_condition_expression,
        }
        if expression_attribute_values:
            params["ExpressionAttributeValues"] = expression_attribute_values
        if expression_attribute_names:
            params["ExpressionAttributeNames"] = expression_attribute_names
        if index_name:
            params["IndexName"] = index_name
        if filter_expression is not None:
            params["FilterExpression"] = filter_expression
        if limit is not None:
            params["Limit"] = limit
        if scan_index_forward is not None:
            params["ScanIndexForward"] = scan_index_forward
        if consistent_read is not None:
            params["ConsistentRead"] = consistent_read

        response = table.query(**params)
        return list(response.get("Items", []))

    def scan(
        self,
        table_name: str,
        filter_expression: Any | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        table = self._resource.Table(table_name)
        params: dict[str, Any] = {}
        if filter_expression is not None:
            params["FilterExpression"] = filter_expression
        if expression_attribute_values:
            params["ExpressionAttributeValues"] = expression_attribute_values
        if expression_attribute_names:
            params["ExpressionAttributeNames"] = expression_attribute_names
        if limit is not None:
            params["Limit"] = limit

        response = table.scan(**params)
        return list(response.get("Items", []))

    def batch_write_items(
        self,
        table_name: str,
        items: list[dict[str, Any]],
    ) -> None:
        table = self._resource.Table(table_name)
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
