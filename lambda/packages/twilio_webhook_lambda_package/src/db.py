from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from src.config import settings


class DynamoStore:

    def __init__(self) -> None:
        dynamodb = boto3.resource("dynamodb")
        self.accounts = dynamodb.Table(settings.accounts_table)
        self.transactions = dynamodb.Table(settings.transactions_table)

    def get_account_by_phone(self, phone_number: str) -> dict[str, Any] | None:
        res = self.accounts.query(
            IndexName="phone_number-index",
            KeyConditionExpression=Key("phone_number").eq(phone_number),
            Limit=1,
        )
        items = res.get("Items", [])
        return items[0] if items else None

    def get_latest_pending_transaction_for_account(self, account_id: str) -> dict[str, Any] | None:
        res = self.transactions.scan(
            FilterExpression="account_id = :a AND pending_confirm = :p",
            ExpressionAttributeValues={":a": account_id, ":p": 1},
        )
        items = res.get("Items", [])
        if not items:
            return None
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[0]

    def update_transaction_fraud_flag(self, transaction_id: str, is_fraud: bool) -> None:
        self.transactions.update_item(
            Key={"transaction_id": transaction_id},
            UpdateExpression="SET is_fraud = :f",
            ExpressionAttributeValues={":f": is_fraud},
        )

    def mark_transaction_pending(self, transaction_id: str, pending: bool) -> None:
        self.transactions.update_item(
            Key={"transaction_id": transaction_id},
            UpdateExpression="SET pending_confirm = :p",
            ExpressionAttributeValues={":p": 1 if pending else 0},
        )