from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Protocol

import boto3

from src.shared.config import settings


class Store(Protocol):
    # Accounts
    def create_account(self, payload: dict[str, Any]) -> None: ...
    def get_account(self, account_id: str) -> dict[str, Any] | None: ...
    def get_account_by_phone(self, phone_number: str) -> dict[str, Any] | None: ...

    # Transactions
    def create_transaction(self, payload: dict[str, Any]) -> None: ...
    def update_transaction_fraud_flag(self, transaction_id: str, is_fraud: bool) -> None: ...
    def mark_transaction_pending(self, transaction_id: str, pending: bool) -> None: ...

    # Pending lists
    def get_pending_transactions_for_account(self, account_id: str, limit: int = 10) -> list[dict[str, Any]]: ...
    def get_latest_pending_transaction_for_account(self, account_id: str) -> dict[str, Any] | None: ...

    # Conversation state
    def set_pending_decision_for_phone(self, phone_number: str, decision: str) -> None: ...
    def get_pending_decision_for_phone(self, phone_number: str) -> str | None: ...
    def clear_pending_decision_for_phone(self, phone_number: str) -> None: ...

    # Debug/demo helpers
    def get_transactions_for_account(self, account_id: str, limit: int = 20) -> list[dict[str, Any]]: ...


# -----------------------------
# DynamoDB implementation (AWS)
# Demo-safe. For production, use GSIs + Query, and store conversation state in Dynamo as well.
# -----------------------------
class DynamoStore:
    _decision_cache: dict[str, str] = {}

    def __init__(self) -> None:
        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.accounts = dynamodb.Table(settings.accounts_table)
        self.transactions = dynamodb.Table(settings.transactions_table)

    # Accounts
    def create_account(self, payload: dict[str, Any]) -> None:
        payload["threshold"] = Decimal(str(payload["threshold"]))
        self.accounts.put_item(Item=payload)

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        res = self.accounts.get_item(Key={"account_id": account_id})
        return res.get("Item")

    def get_account_by_phone(self, phone_number: str) -> dict[str, Any] | None:
        res = self.accounts.scan(
            FilterExpression="phone_number = :p",
            ExpressionAttributeValues={":p": phone_number},
            Limit=1,
        )
        items = res.get("Items", [])
        return items[0] if items else None

    # Transactions
    def create_transaction(self, payload: dict[str, Any]) -> None:
        payload["amount"] = Decimal(str(payload["amount"]))
        payload["score"] = Decimal(str(payload.get("score", 0.0)))
        payload["pending_confirm"] = int(payload.get("pending_confirm", 0))
        self.transactions.put_item(Item=payload)

    def update_transaction_fraud_flag(self, transaction_id: str, is_fraud: bool) -> None:
        self.transactions.update_item(
            Key={"transaction_id": transaction_id},
            UpdateExpression="SET #f = :f",
            ExpressionAttributeNames={"#f": "is_fraud"},
            ExpressionAttributeValues={":f": is_fraud},
        )

    def mark_transaction_pending(self, transaction_id: str, pending: bool) -> None:
        self.transactions.update_item(
            Key={"transaction_id": transaction_id},
            UpdateExpression="SET pending_confirm = :p",
            ExpressionAttributeValues={":p": 1 if pending else 0},
        )

    # Pending lists
    def get_pending_transactions_for_account(self, account_id: str, limit: int = 10) -> list[dict[str, Any]]:
        res = self.transactions.scan(
            FilterExpression="account_id = :a AND pending_confirm = :p",
            ExpressionAttributeValues={":a": account_id, ":p": 1},
        )
        items = res.get("Items", [])
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]

    def get_latest_pending_transaction_for_account(self, account_id: str) -> dict[str, Any] | None:
        pending = self.get_pending_transactions_for_account(account_id, limit=1)
        return pending[0] if pending else None

    # Conversation state (demo-only)
    def set_pending_decision_for_phone(self, phone_number: str, decision: str) -> None:
        self._decision_cache[phone_number] = decision

    def get_pending_decision_for_phone(self, phone_number: str) -> str | None:
        return self._decision_cache.get(phone_number)

    def clear_pending_decision_for_phone(self, phone_number: str) -> None:
        self._decision_cache.pop(phone_number, None)

    # Debug/demo
    def get_transactions_for_account(self, account_id: str, limit: int = 20) -> list[dict[str, Any]]:
        res = self.transactions.scan(
            FilterExpression="account_id = :a",
            ExpressionAttributeValues={":a": account_id},
        )
        items = res.get("Items", [])
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]


# -----------------------------
# SQLite implementation (LOCAL)
# -----------------------------
class SQLiteStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    threshold REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    merchant TEXT,
                    location TEXT,
                    timestamp INTEGER,
                    score REAL NOT NULL DEFAULT 0.0,
                    is_fraud INTEGER NULL,
                    pending_confirm INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_state (
                    phone_number TEXT PRIMARY KEY,
                    decision TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            cols = {row["name"] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()}
            if "pending_confirm" not in cols:
                conn.execute("ALTER TABLE transactions ADD COLUMN pending_confirm INTEGER NOT NULL DEFAULT 0")
            if "created_at" not in cols:
                conn.execute("ALTER TABLE transactions ADD COLUMN created_at TEXT")

    # Accounts
    def create_account(self, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO accounts(account_id, phone_number, threshold)
                VALUES (?, ?, ?)
                """,
                (payload["account_id"], payload["phone_number"], float(payload["threshold"])),
            )

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT account_id, phone_number, threshold FROM accounts WHERE account_id=?",
                (account_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_account_by_phone(self, phone_number: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT account_id, phone_number, threshold FROM accounts WHERE phone_number=?",
                (phone_number,),
            ).fetchone()
            return dict(row) if row else None

    # Transactions
    def create_transaction(self, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO transactions(
                    transaction_id, account_id, amount, merchant, location, timestamp,
                    score, is_fraud, pending_confirm, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["transaction_id"],
                    payload["account_id"],
                    float(payload["amount"]),
                    payload.get("merchant"),
                    payload.get("location"),
                    payload.get("timestamp"),
                    float(payload.get("score", 0.0)),
                    None if payload.get("is_fraud", None) is None else (1 if payload["is_fraud"] else 0),
                    int(payload.get("pending_confirm", 0)),
                    payload.get("created_at"),
                ),
            )

    def update_transaction_fraud_flag(self, transaction_id: str, is_fraud: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE transactions SET is_fraud=? WHERE transaction_id=?",
                (1 if is_fraud else 0, transaction_id),
            )

    def mark_transaction_pending(self, transaction_id: str, pending: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE transactions SET pending_confirm=? WHERE transaction_id=?",
                (1 if pending else 0, transaction_id),
            )

    # Pending lists
    def get_pending_transactions_for_account(self, account_id: str, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT transaction_id, account_id, amount, merchant, location, timestamp,
                       score, is_fraud, pending_confirm, created_at
                FROM transactions
                WHERE account_id=? AND pending_confirm=1
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()

            out: list[dict[str, Any]] = []
            for r in rows:
                d = dict(r)
                d["pending_confirm"] = int(d.get("pending_confirm", 0))
                if d["is_fraud"] is not None:
                    d["is_fraud"] = bool(d["is_fraud"])
                out.append(d)
            return out

    def get_latest_pending_transaction_for_account(self, account_id: str) -> dict[str, Any] | None:
        pending = self.get_pending_transactions_for_account(account_id, limit=1)
        return pending[0] if pending else None

    # Conversation state
    def set_pending_decision_for_phone(self, phone_number: str, decision: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO conversation_state(phone_number, decision, updated_at)
                VALUES (?, ?, ?)
                """,
                (phone_number, decision, datetime.now(timezone.utc).isoformat()),
            )

    def get_pending_decision_for_phone(self, phone_number: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT decision FROM conversation_state WHERE phone_number=?",
                (phone_number,),
            ).fetchone()
            return str(row["decision"]) if row else None

    def clear_pending_decision_for_phone(self, phone_number: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM conversation_state WHERE phone_number=?", (phone_number,))

    # Debug/demo
    def get_transactions_for_account(self, account_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT transaction_id, account_id, amount, merchant, location, timestamp,
                       score, is_fraud, pending_confirm, created_at
                FROM transactions
                WHERE account_id=?
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()

            out: list[dict[str, Any]] = []
            for r in rows:
                d = dict(r)
                d["pending_confirm"] = int(d.get("pending_confirm", 0))
                if d["is_fraud"] is not None:
                    d["is_fraud"] = bool(d["is_fraud"])
                out.append(d)
            return out


# -----------------------------
# Factory
# -----------------------------
_store: Optional[Store] = None


def get_store() -> Store:
    global _store
    if _store is not None:
        return _store
    _store = SQLiteStore(settings.sqlite_path) if settings.local_mode else DynamoStore()
    return _store