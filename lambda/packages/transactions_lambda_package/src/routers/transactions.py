import json
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config import settings
from src.db import DynamoStore
from src.scorer import get_scorer

router = APIRouter(prefix="/transactions", tags=["Transactions"])


class CreateTransactionRequest(BaseModel):
    phone_number: str
    amount: float = Field(..., gt=0)
    merchant: str
    category: str
    state: str


@router.post("")
def create_transaction(payload: CreateTransactionRequest) -> dict:
    db = DynamoStore()

    account = db.get_account_by_phone(payload.phone_number)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    scorer = get_scorer()
    score = scorer.score({
        **payload.model_dump(),
        "home_state": account.get("home_state", ""),
        "dob": account.get("dob", ""),
    })

    transaction_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    db.create_transaction({
        "transaction_id": transaction_id,
        "account_id": account["account_id"],
        "amount": payload.amount,
        "merchant": payload.merchant,
        "category": payload.category,
        "state": payload.state,
        "score": score,
        "is_fraud": False,
        "created_at": now,
    })

    threshold = float(account.get("threshold", 0.8))
    flagged = score >= threshold

    if flagged and settings.sqs_queue_url:
        sqs = boto3.client("sqs")
        sqs.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps({
                "transaction_id": transaction_id,
                "account_id": account["account_id"],
                "amount": payload.amount,
                "merchant": payload.merchant,
                "score": score,
                "phone_number": payload.phone_number,
                "state": payload.state
            }),
        )

    return {
        "transaction_id": transaction_id,
        "score": score,
        "flagged": flagged,
    }