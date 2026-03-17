from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from src.config import settings


class DynamoStore:

    def __init__(self) -> None:
        dynamodb = boto3.resource("dynamodb")
        self.accounts = dynamodb.Table(settings.accounts_table)
        self.transactions = dynamodb.Table(settings.transactions_table)

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        res = self.accounts.get_item(Key={"account_id": account_id})
        return res.get("Item")

    def mark_transaction_pending(self, transaction_id: str, pending: bool) -> None:
        self.transactions.update_item(
            Key={"transaction_id": transaction_id},
            UpdateExpression="SET pending_confirm = :p",
            ExpressionAttributeValues={":p": 1 if pending else 0},
        )