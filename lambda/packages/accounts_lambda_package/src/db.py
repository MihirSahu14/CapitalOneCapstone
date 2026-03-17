from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from src.config import settings


class DynamoStore:

    def __init__(self) -> None:
        dynamodb = boto3.resource("dynamodb")
        self.accounts = dynamodb.Table(settings.accounts_table)
        self.transactions = dynamodb.Table(settings.transactions_table)

    def create_account(self, payload: dict[str, Any]) -> None:
        payload["threshold"] = Decimal(str(payload["threshold"]))
        self.accounts.put_item(Item=payload)

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        res = self.accounts.get_item(Key={"account_id": account_id})
        return res.get("Item")

    def get_account_by_phone(self, phone_number: str) -> dict[str, Any] | None:
        res = self.accounts.query(
            IndexName="phone_number-index",
            KeyConditionExpression=Key("phone_number").eq(phone_number),
            Limit=1,
        )
        items = res.get("Items", [])
        return items[0] if items else None

    def delete_account(self, account_id: str) -> None:
        self.accounts.delete_item(Key={"account_id": account_id})

    def get_transactions_for_account(self, account_id: str, limit: int = 20) -> list[dict[str, Any]]:
        res = self.transactions.scan(
            FilterExpression="account_id = :a",
            ExpressionAttributeValues={":a": account_id},
        )
        items = res.get("Items", [])
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]