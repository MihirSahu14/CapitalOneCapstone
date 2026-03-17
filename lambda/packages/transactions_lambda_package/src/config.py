import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    accounts_table: str = os.getenv("ACCOUNTS_TABLE", "accounts")
    transactions_table: str = os.getenv("TRANSACTIONS_TABLE", "transactions")
    model_s3_bucket: str = os.getenv("MODEL_S3_BUCKET", "fraud-detection-model-1234")
    model_s3_key: str = os.getenv("MODEL_S3_KEY", "model.joblib")
    sqs_queue_url: str = os.getenv("SQS_QUEUE_URL", "")


settings = Settings()