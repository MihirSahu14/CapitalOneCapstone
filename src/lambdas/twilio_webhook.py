from __future__ import annotations

from urllib.parse import parse_qs

from src.shared.db import DynamoStore

db = DynamoStore()


def lambda_handler(event: dict, _context: dict) -> dict:
    body = parse_qs(event.get("body", ""))
    sms_text = body.get("Body", [""])[0].strip().upper()
    message_sid = body.get("MessageSid", [""])[0]

    # In production, map message SID -> transaction_id in a dedicated table.
    # Here we expect transaction_id to be passed as a query parameter.
    query = event.get("queryStringParameters") or {}
    transaction_id = query.get("transaction_id")
    if not transaction_id:
        return {"statusCode": 400, "body": "Missing transaction_id"}

    if sms_text == "YES":
        db.update_transaction_fraud_flag(transaction_id, True)
    elif sms_text == "NO":
        db.update_transaction_fraud_flag(transaction_id, False)
    else:
        return {"statusCode": 200, "body": f"Ignored message {message_sid}"}

    return {"statusCode": 200, "body": f"Updated transaction {transaction_id}"}
