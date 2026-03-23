from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.db import DynamoStore

router = APIRouter(prefix="/accounts", tags=["Accounts"])


class CreateAccountRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 format, e.g. +16085551234")
    threshold: float = Field(0.8, ge=0.0, le=1.0)

class UpdateThresholdRequest(BaseModel):
    threshold: float = Field(..., ge=0.0, le=1.0, description="New fraud detection threshold (0.0-1.0)")

@router.post("")
def create_account(payload: CreateAccountRequest) -> dict:
    db = DynamoStore()
    existing = db.get_account_by_phone(payload.phone_number)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this phone number already exists")

    account_id = str(uuid4())
    now = datetime.now(timezone.utc)
    db.create_account({
        "account_id": account_id,
        "phone_number": payload.phone_number,
        "threshold": payload.threshold,
        "created_at": now.isoformat(),
    })
    return {"account_id": account_id}


@router.get("/by-phone/{phone_number}")
def get_account_by_phone(phone_number: str, limit: int = 20) -> dict:
    db = DynamoStore()
    acct = db.get_account_by_phone(phone_number)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    txs = db.get_transactions_for_account(acct["account_id"], limit=limit)
    return {"account": acct, "transactions": txs}


@router.delete("/by-phone/{phone_number}")
def delete_account(phone_number: str) -> dict:
    db = DynamoStore()
    existing = db.get_account_by_phone(phone_number)
    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete_account(existing["account_id"])
    return {"deleted": existing["account_id"]}


@router.patch("/by-phone/{phone_number}/threshold")
def update_threshold_by_phone(phone_number: str, payload: UpdateThresholdRequest) -> dict:
    db = DynamoStore()

    # Look up account by phone
    account = db.get_account_by_phone(phone_number)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account_id = account["account_id"]
    old_threshold = float(account.get("threshold", 0.8))

    # Update threshold
    db.update_threshold(account_id, payload.threshold)

    return {
        "account_id": account_id,
        "phone_number": phone_number,
        "old_threshold": old_threshold,
        "new_threshold": payload.threshold,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }