from __future__ import annotations

from decimal import Decimal
from typing import Any

import boto3

from src.shared.config import settings


class DynamoStore:
    def __init__(self) -> None:
        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.accounts = dynamodb.Table(settings.accounts_table)
        self.transactions = dynamodb.Table(settings.transactions_table)

    def create_account(self, payload: dict[str, Any]) -> None:
        payload["threshold"] = Decimal(str(payload["threshold"]))
        self.accounts.put_item(Item=payload)

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        res = self.accounts.get_item(Key={"account_id": account_id})
        return res.get("Item")

    def create_transaction(self, payload: dict[str, Any]) -> None:
        payload["amount"] = Decimal(str(payload["amount"]))
        payload["score"] = Decimal(str(payload.get("score", 0.0)))
        payload["is_fraud"] = payload.get("is_fraud", None)
        self.transactions.put_item(Item=payload)

    def update_transaction_score(self, transaction_id: str, score: float) -> None:
        self.transactions.update_item(
            Key={"transaction_id": transaction_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "score"},
            ExpressionAttributeValues={":s": Decimal(str(score))},
        )

    def update_transaction_fraud_flag(self, transaction_id: str, is_fraud: bool) -> None:
        self.transactions.update_item(
            Key={"transaction_id": transaction_id},
            UpdateExpression="SET #f = :f",
            ExpressionAttributeNames={"#f": "is_fraud"},
            ExpressionAttributeValues={":f": is_fraud},
        )
