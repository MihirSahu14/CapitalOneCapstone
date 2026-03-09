#!/usr/bin/env bash
set -e

echo "==> Starting ngrok on port 8000"
ngrok http 8000
