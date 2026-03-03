from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from mangum import Mangum
from pydantic import BaseModel, Field
from twilio.rest import Client

from src.model.scorer import FraudScorer
from src.shared.config import settings
from src.shared.db import get_store

# Load model once
scorer = FraudScorer.load(settings.model_path)

app = FastAPI(title="Fraud Detection System API", version="0.1.0")
db = get_store()
lambda_handler = Mangum(app)  # keep for AWS later; harmless locally

twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token) if (
    settings.twilio_account_sid and settings.twilio_auth_token
) else None


class CreateAccountRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 format, ex: +16085551234")
    threshold: float = Field(0.8, ge=0.0, le=1.0)


class CreateTransactionRequest(BaseModel):
    account_id: str
    amount: float
    merchant: str
    location: str


def get_timezone_for_location(location: str) -> str:
    """
    Very simple demo mapping.
    We can expand as needed.
    """
    location = location.lower()

    if "chicago" in location or "illinois" in location:
        return "America/Chicago"
    if "new york" in location:
        return "America/New_York"
    if "california" in location or "los angeles" in location:
        return "America/Los_Angeles"
    if "texas" in location:
        return "America/Chicago"
    if "london" in location:
        return "Europe/London"

    # Default fallback
    return "UTC"


def build_alert_message(
    amount: float,
    merchant: str,
    location: str,
    timestamp_utc: int,
) -> str:
    tz_name = get_timezone_for_location(location)
    tz = ZoneInfo(tz_name)

    dt_local = (
        datetime.fromtimestamp(timestamp_utc, tz=timezone.utc)
        .astimezone(tz)
    )

    formatted_date = dt_local.strftime("%B %d, %Y")
    formatted_time = dt_local.strftime("%I:%M %p %Z")

    return (
        "*Sentinel Fraud Alert*\n\n"
        "We detected a transaction that may be unauthorized.\n"
        "```\n"
        f"Amount   : ${amount:.2f}\n"
        f"Merchant : {merchant}\n"
        f"Location : {location}\n"
        f"Date     : {formatted_date}\n"
        f"Time     : {formatted_time}\n"
        "```\n"
        "Was this you?\n"
        "Reply YES to confirm.\n"
        "Reply NO if you do not recognize it."
    )


def send_alert_whatsapp(to_number: str, message: str) -> None:
    if twilio_client is None or not settings.twilio_whatsapp_from:
        print("[WARN] Twilio WhatsApp not configured. Would send:", to_number, message)
        return

    to_wp = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"

    twilio_client.messages.create(
        to=to_wp,
        from_=settings.twilio_whatsapp_from,
        body=message,
    )


@app.post("/accounts")
def create_account(payload: CreateAccountRequest) -> dict:
    account_id = str(uuid4())
    now = datetime.now(timezone.utc)

    db.create_account(
        {
            "account_id": account_id,
            "phone_number": payload.phone_number,
            "threshold": payload.threshold,
            "created_at": now.isoformat(),
        }
    )
    return {"account_id": account_id}


@app.post("/transactions")
def create_transaction(payload: CreateTransactionRequest) -> dict:
    account = db.get_account(payload.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    now = datetime.now(timezone.utc)
    timestamp_utc = int(now.timestamp())

    tx_input = payload.model_dump()
    tx_score = scorer.score(tx_input)

    transaction_id = str(uuid4())
    threshold = float(account["threshold"])

    db.create_transaction(
        {
            "transaction_id": transaction_id,
            "account_id": payload.account_id,
            "amount": payload.amount,
            "merchant": payload.merchant,
            "location": payload.location,
            "timestamp": timestamp_utc,
            "score": tx_score,
            "is_fraud": None,
            "pending_confirm": 0,
            "created_at": now.isoformat(),
        }
    )

    if tx_score >= threshold:
        msg = build_alert_message(
            amount=payload.amount,
            merchant=payload.merchant,
            location=payload.location,
            timestamp_utc=timestamp_utc,
        )
        send_alert_whatsapp(account["phone_number"], msg)
        db.mark_transaction_pending(transaction_id, True)

    return {"transaction_id": transaction_id, "score": tx_score, "threshold": threshold}


@app.post("/twilio/webhook")
async def twilio_webhook(request: Request) -> Response:
    form = await request.form()

    from_number = str(form.get("From", "")).strip()  # "whatsapp:+1..."
    decision = str(form.get("Body", "")).strip().upper()

    if decision not in {"YES", "NO"}:
        return Response(
            content="<Response><Message>Reply YES to confirm or NO to report fraud.</Message></Response>",
            media_type="text/xml",
        )

    phone = from_number.replace("whatsapp:", "")

    acct = db.get_account_by_phone(phone)
    if not acct:
        return Response(
            content="<Response><Message>Account not found for this number.</Message></Response>",
            media_type="text/xml",
        )

    tx = db.get_latest_pending_transaction_for_account(acct["account_id"])
    if not tx:
        return Response(
            content="<Response><Message>No pending fraud alert found.</Message></Response>",
            media_type="text/xml",
        )

    is_fraud = (decision == "NO")
    db.update_transaction_fraud_flag(tx["transaction_id"], is_fraud)
    db.mark_transaction_pending(tx["transaction_id"], False)

    reply = "Approved.\nThank you." if not is_fraud else "Reported as fraud.\nThank you."
    return Response(
        content=f"<Response><Message>{reply}</Message></Response>",
        media_type="text/xml",
    )


@app.get("/accounts/by-phone/{phone_number}")
def get_account_by_phone(phone_number: str, limit: int = 20):
    acct = db.get_account_by_phone(phone_number)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")

    txs = db.get_transactions_for_account(acct["account_id"], limit=limit)
    return {"account": acct, "transactions": txs}