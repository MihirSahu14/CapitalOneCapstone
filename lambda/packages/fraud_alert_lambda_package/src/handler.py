import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from twilio.rest import Client
from src.config import settings
from src.db import DynamoStore


def get_timezone_for_state(state: str) -> str:
    eastern = {"NY", "FL", "NC", "SC", "VA", "PA", "NJ", "MD", "CT", "MA", "ME", "VT", "NH", "RI", "DE", "WV", "OH", "MI", "IN", "KY", "TN", "GA", "AL"}
    central = {"TX", "IL", "WI", "MN", "IA", "MO", "AR", "LA", "MS", "OK", "KS", "NE", "SD", "ND"}
    mountain = {"CO", "UT", "AZ", "NM", "WY", "MT", "ID"}
    pacific = {"CA", "OR", "WA", "NV"}

    if state in eastern:  return "America/New_York"
    if state in central:  return "America/Chicago"
    if state in mountain: return "America/Denver"
    if state in pacific:  return "America/Los_Angeles"
    return "UTC"


def build_alert_message(amount: float, merchant: str, state: str) -> str:
    now = datetime.now(timezone.utc)
    tz = ZoneInfo(get_timezone_for_state(state))
    dt_local = now.astimezone(tz)
    formatted_date = dt_local.strftime("%B %d, %Y")
    formatted_time = dt_local.strftime("%I:%M %p %Z")

    return (
        "*Sentinel Fraud Alert*\n\n"
        "We detected a transaction that may be unauthorized.\n"
        "```\n"
        f"Amount   : ${amount:.2f}\n"
        f"Merchant : {merchant}\n"
        f"State    : {state}\n"
        f"Date     : {formatted_date}\n"
        f"Time     : {formatted_time}\n"
        "```\n"
        "Was this you?\n"
        "Reply YES to confirm.\n"
        "Reply NO if you do not recognize it."
    )


def send_whatsapp(to_number: str, message: str) -> None:
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        print(f"[WARN] Twilio not configured. Would send to {to_number}: {message}")
        return

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    to_wp = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
    client.messages.create(
        to=to_wp,
        from_=settings.twilio_whatsapp_from,
        body=message,
    )
    print(f"WhatsApp alert sent to {to_number}")


def lambda_handler(event: dict, context: object) -> dict:
    db = DynamoStore()
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        transaction_id = body["transaction_id"]
        amount = float(body["amount"])
        merchant = body["merchant"]
        phone_number = body["phone_number"]
        state = body.get("state", "")

        # Send WhatsApp — if this fails, SQS will retry
        msg = build_alert_message(amount, merchant, state)
        send_whatsapp(phone_number, msg)

        # Mark pending — if this fails, log but don't retry
        # (WhatsApp already sent, no point resending)
        try:
            db.mark_transaction_pending(transaction_id, True)
        except Exception as e:
            print(f"[WARN] Could not mark transaction pending: {e}")

        print(f"Processed transaction {transaction_id}")

    return {"statusCode": 200}