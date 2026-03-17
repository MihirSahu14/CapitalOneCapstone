from decimal import Decimal
from typing import Any

import boto3
from src.config import settings


class DynamoStore:

    def __init__(self) -> None:
        dynamodb = boto3.resource("dynamodb")
        self.accounts = dynamodb.Table(settings.accounts_table)
        self.transactions = dynamodb.Table(settings.transactions_table)

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        res = self.accounts.get_item(Key={"account_id": account_id})
        return res.get("Item")

    def create_transaction(self, payload: dict[str, Any]) -> None:
        payload["amount"] = Decimal(str(payload["amount"]))
        payload["score"] = Decimal(str(payload.get("score", 0.0)))
        self.transactions.put_item(Item=payload)

    def get_account_by_phone(self, phone_number: str) -> dict[str, Any] | None:
        from boto3.dynamodb.conditions import Key
        res = self.accounts.query(
            IndexName="phone_number-index",
            KeyConditionExpression=Key("phone_number").eq(phone_number),
            Limit=1,
        )
        items = res.get("Items", [])
        return items[0] if items else None