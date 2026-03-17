import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    accounts_table: str = os.getenv("ACCOUNTS_TABLE", "accounts")
    transactions_table: str = os.getenv("TRANSACTIONS_TABLE", "transactions")


settings = Settings()