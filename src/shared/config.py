from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    accounts_table: str = os.getenv("ACCOUNTS_TABLE", "Accounts")
    transactions_table: str = os.getenv("TRANSACTIONS_TABLE", "Transactions")
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from_number: str = os.getenv("TWILIO_FROM_NUMBER", "")
    model_path: str = os.getenv("MODEL_PATH", "data/processed/model.joblib")


settings = Settings()
