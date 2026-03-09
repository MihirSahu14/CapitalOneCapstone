#!/usr/bin/env bash
set -e

DB="data/processed/local.db"

if [ ! -f "$DB" ]; then
  echo "Database not found at $DB"
  exit 1
fi

sqlite3 "$DB" <<'EOF'
.headers on
.mode table

.print "\n========== TABLES =========="
.tables

.print "\n========== ACCOUNTS =========="
SELECT * FROM accounts;

.print "\n========== TRANSACTIONS =========="
SELECT * FROM transactions;

.print "\n========== CONVERSATION STATE =========="
SELECT * FROM conversation_state;

.print "\n========== END =========="
EOF
