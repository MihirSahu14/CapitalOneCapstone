from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from mangum import Mangum
from pydantic import BaseModel, Field

from src.model.scorer import FraudScorer
from src.shared.config import settings
from src.shared.db import DynamoStore

app = FastAPI(title="Fraud Detection System API", version="0.1.0")
db = DynamoStore()
lambda_handler = Mangum(app)


class CreateAccountRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 format, ex: +16085551234")
    threshold: float = Field(0.8, ge=0.0, le=1.0)


class CreateTransactionRequest(BaseModel):
    account_id: str
    amount: float
    merchant: str
    location: str
    timestamp: int = Field(..., description="Unix timestamp in seconds")


@app.post("/accounts")
def create_account(payload: CreateAccountRequest) -> dict:
    account_id = str(uuid4())
    db.create_account(
        {
            "account_id": account_id,
            "phone_number": payload.phone_number,
            "threshold": payload.threshold,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return {"account_id": account_id}


@app.post("/transactions")
def create_transaction(payload: CreateTransactionRequest) -> dict:
    account = db.get_account(payload.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    scorer = FraudScorer.load(settings.model_path)
    tx_score = scorer.score(payload.model_dump())
    transaction_id = str(uuid4())
    db.create_transaction(
        {
            "transaction_id": transaction_id,
            "account_id": payload.account_id,
            "amount": payload.amount,
            "merchant": payload.merchant,
            "location": payload.location,
            "timestamp": payload.timestamp,
            "score": tx_score,
            "is_fraud": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return {"transaction_id": transaction_id, "score": tx_score, "threshold": float(account["threshold"])}
