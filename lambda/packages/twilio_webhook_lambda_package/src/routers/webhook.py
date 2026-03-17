from fastapi import APIRouter, Request, Response
from src.db import DynamoStore

router = APIRouter(tags=["Webhook"])

TWIML_REASK = (
    "<Response><Message>"
    "Sorry, I didn't understand that.\n\n"
    "Please reply *YES* if you made this transaction, "
    "or *NO* if you did not recognize it."
    "</Message></Response>"
)

TWIML_CONFIRMED = (
    "<Response><Message>"
    "Approved.\n"
    "Thank you."
    "</Message></Response>"
)

TWIML_FRAUD = (
    "<Response><Message>"
    "Reported as fraud.\n"
    "Thank you."
    "</Message></Response>"
)

TWIML_NO_ACCOUNT = (
    "<Response><Message>"
    "We could not find an account associated with this number."
    "</Message></Response>"
)

TWIML_NO_PENDING = (
    "<Response><Message>"
    "No pending fraud alert found for your account."
    "</Message></Response>"
)


@router.post("/twilio/webhook")
async def twilio_webhook(request: Request) -> Response:
    form = await request.form()

    from_number = str(form.get("From", "")).strip()
    raw_body    = str(form.get("Body", "")).strip()
    decision    = raw_body.upper()

    # Validate response
    if decision not in {"YES", "NO"}:
        return Response(content=TWIML_REASK, media_type="text/xml")

    # Strip whatsapp: prefix to get plain phone number
    phone = from_number.replace("whatsapp:", "").strip()

    db = DynamoStore()

    # Look up account
    acct = db.get_account_by_phone(phone)
    if not acct:
        return Response(content=TWIML_NO_ACCOUNT, media_type="text/xml")

    # Get latest pending transaction
    tx = db.get_latest_pending_transaction_for_account(acct["account_id"])
    if not tx:
        return Response(content=TWIML_NO_PENDING, media_type="text/xml")

    # YES → user recognizes it → NOT fraud
    # NO  → user doesn't recognize it → IS fraud
    is_fraud = (decision == "NO")
    db.update_transaction_fraud_flag(tx["transaction_id"], is_fraud)
    db.mark_transaction_pending(tx["transaction_id"], False)

    reply = TWIML_FRAUD if is_fraud else TWIML_CONFIRMED
    return Response(content=reply, media_type="text/xml")