from datetime import datetime, timezone
from uuid import uuid4
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.db import DynamoStore

router = APIRouter(prefix="/accounts", tags=["Accounts"])

VALID_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
}

E164_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")


class CreateAccountRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 format, e.g. +16085551234")
    threshold: float = Field(0.8, ge=0.0, le=1.0)
    home_state: str = Field(..., description="2-letter US state code, e.g. WI")
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format, e.g. 1990-05-15")


class UpdateThresholdRequest(BaseModel):
    threshold: float = Field(..., ge=0.0, le=1.0, description="New fraud detection threshold (0.0-1.0)")


@router.post("")
def create_account(payload: CreateAccountRequest) -> dict:
    db = DynamoStore()

    home_state = payload.home_state.upper().strip()
    if home_state not in VALID_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid home_state '{home_state}'. Must be a 2-letter US state code."
        )

    try:
        datetime.strptime(payload.dob, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dob format. Use YYYY-MM-DD.")

    if not E164_REGEX.match(payload.phone_number):
        raise HTTPException(
            status_code=400,
            detail="Invalid phone_number. Must be E.164 format, e.g. +16085551234"
        )

    existing = db.get_account_by_phone(payload.phone_number)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this phone number already exists")

    account_id = str(uuid4())
    now = datetime.now(timezone.utc)
    db.create_account({
        "account_id": account_id,
        "phone_number": payload.phone_number,
        "threshold": payload.threshold,
        "home_state": home_state,
        "dob": payload.dob,
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
    account = db.get_account_by_phone(phone_number)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account_id = account["account_id"]
    old_threshold = float(account.get("threshold", 0.8))
    db.update_threshold(account_id, payload.threshold)

    return {
        "account_id": account_id,
        "phone_number": phone_number,
        "old_threshold": old_threshold,
        "new_threshold": payload.threshold,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }