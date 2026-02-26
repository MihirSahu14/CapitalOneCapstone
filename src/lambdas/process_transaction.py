from __future__ import annotations

from twilio.rest import Client

from src.model.scorer import FraudScorer
from src.shared.config import settings
from src.shared.db import DynamoStore

db = DynamoStore()
scorer = FraudScorer.load(settings.model_path)


def lambda_handler(event: dict, _context: dict) -> dict:
    record = event["detail"]
    account_id = record["account_id"]
    transaction_id = record["transaction_id"]

    account = db.get_account(account_id)
    score = scorer.score(record)
    db.update_transaction_score(transaction_id, score)

    threshold = float(account["threshold"])
    if score >= threshold:
        send_fraud_sms(account["phone_number"], transaction_id, score)

    return {"transaction_id": transaction_id, "score": score}


def send_fraud_sms(phone_number: str, transaction_id: str, score: float) -> None:
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    body = (
        f"Fraud alert: transaction {transaction_id} scored {score:.2f}. "
        "Reply YES if this was fraud, NO if it was legitimate."
    )
    client.messages.create(to=phone_number, from_=settings.twilio_from_number, body=body)
