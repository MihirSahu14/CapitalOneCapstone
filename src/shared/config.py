from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Mode
    local_mode: bool = os.getenv("LOCAL_MODE", "0") == "1"

    # AWS (used when local_mode=0)
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    accounts_table: str = os.getenv("ACCOUNTS_TABLE", "Accounts")
    transactions_table: str = os.getenv("TRANSACTIONS_TABLE", "Transactions")

    # Twilio
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    # Keeping this for future SMS mode (unused for WhatsApp sandbox)
    twilio_from_number: str = os.getenv("TWILIO_FROM_NUMBER", "")
    # WhatsApp Sandbox sender, default is Twilio sandbox number
    twilio_whatsapp_from: str = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    # Model
    model_path: str = os.getenv("MODEL_PATH", "data/processed/model.joblib")

    # Local DB
    sqlite_path: str = os.getenv("SQLITE_PATH", "data/processed/local.db")


settings = Settings()