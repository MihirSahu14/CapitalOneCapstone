#!/bin/bash
# =============================================================================
# Sentinel Lambda Setup Script
# =============================================================================
# This script installs dependencies, zips, and deploys all 4 Lambda functions
# to both AWS regions (us-east-2 and us-west-2).
#
# Prerequisites:
#   - Python 3.12
#   - pip
#   - AWS CLI configured with access to the CapitalOneCapstone account
#     Run: aws configure
#     Required: Access Key, Secret Key, default region = us-east-2
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# What this script does:
#   1. Installs Linux-compatible dependencies for each Lambda package
#   2. Removes boto3/botocore (provided by AWS Lambda runtime — no need to bundle)
#   3. Handles onnxruntime separately (requires a different Linux platform tag)
#   4. Zips each package (excluding junk files)
#   5. Deploys each zip to both us-east-2 and us-west-2
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE="$SCRIPT_DIR/packages"
ZIP_DIR="$SCRIPT_DIR/zip"
PLATFORM="manylinux2014_x86_64"
PYTHON_VERSION="3.12"
PRIMARY_REGION="us-east-2"
SECONDARY_REGION="us-west-2"

mkdir -p "$ZIP_DIR"

# =============================================================================
# STEP 1 — Install dependencies for all packages
# =============================================================================

packages=(
  "accounts_lambda_package"
  "fraud_alert_lambda_package"
  "twilio_webhook_lambda_package"
)

# Install standard packages (excluding transactions — handled separately below)
for pkg in "${packages[@]}"; do
  echo "[1/4] Installing dependencies for $pkg..."
  pip install \
    -r "$BASE/$pkg/requirements.txt" \
    --target "$BASE/$pkg" \
    --platform $PLATFORM \
    --python-version $PYTHON_VERSION \
    --only-binary=:all: \
    --upgrade \
    --quiet
  echo "      Removing boto3/botocore (provided by Lambda runtime)..."
  rm -rf "$BASE/$pkg/boto3" "$BASE/$pkg/botocore"
  echo "      Done: $pkg"
done

# transactions_lambda_package — install standard deps first
echo "[1/4] Installing dependencies for transactions_lambda_package..."
pip install \
  -r "$BASE/transactions_lambda_package/requirements.txt" \
  --target "$BASE/transactions_lambda_package" \
  --platform $PLATFORM \
  --python-version $PYTHON_VERSION \
  --only-binary=:all: \
  --upgrade \
  --quiet \
  --ignore-requires-python || true

# onnxruntime requires a different platform tag (manylinux_2_27) —
# it is NOT available under manylinux2014, so we download it separately
echo "      Installing onnxruntime for Linux (manylinux_2_27_x86_64)..."
pip download onnxruntime==1.24.3 \
  --dest /tmp/onnx_whl \
  --platform manylinux_2_27_x86_64 \
  --python-version $PYTHON_VERSION \
  --only-binary=:all: \
  --no-deps \
  --quiet
unzip -o /tmp/onnx_whl/onnxruntime*.whl -d "$BASE/transactions_lambda_package" > /dev/null
rm -rf /tmp/onnx_whl

echo "      Removing boto3/botocore (provided by Lambda runtime)..."
rm -rf "$BASE/transactions_lambda_package/boto3" "$BASE/transactions_lambda_package/botocore"
echo "      Done: transactions_lambda_package"

# =============================================================================
# STEP 2 — Zip each package
# =============================================================================

echo ""
echo "[2/4] Zipping packages..."

all_packages=(
  "accounts_lambda_package"
  "transactions_lambda_package"
  "fraud_alert_lambda_package"
  "twilio_webhook_lambda_package"
)

for pkg in "${all_packages[@]}"; do
  echo "      Zipping $pkg..."
  cd "$BASE/$pkg"
  zip -r "$ZIP_DIR/${pkg}.zip" . \
    -x "*.DS_Store" \
    -x "__pycache__/*" \
    -x "*.pyc" \
    -x "*.pyo" \
    -x "*.dist-info/*" \
    > /dev/null
  cd "$SCRIPT_DIR"
  echo "      Done: $ZIP_DIR/${pkg}.zip"
done

# =============================================================================
# STEP 3 — Deploy to both AWS regions
# =============================================================================

echo ""
echo "[3/4] Deploying to $PRIMARY_REGION and $SECONDARY_REGION..."

deploy() {
  local function_name=$1
  local zip_name=$2
  echo "      Deploying $function_name..."
  aws lambda update-function-code \
    --function-name "$function_name" \
    --zip-file "fileb://$ZIP_DIR/${zip_name}.zip" \
    --region $PRIMARY_REGION \
    --output text --query 'LastUpdateStatus'
  aws lambda update-function-code \
    --function-name "$function_name" \
    --zip-file "fileb://$ZIP_DIR/${zip_name}.zip" \
    --region $SECONDARY_REGION \
    --output text --query 'LastUpdateStatus'
  echo "      Done: $function_name → both regions"
}

deploy "accounts-api"       "accounts_lambda_package"
deploy "transactions-api"   "transactions_lambda_package"
deploy "fraud-alert-api"    "fraud_alert_lambda_package"
deploy "twilio-webhook-api" "twilio_webhook_lambda_package"

# =============================================================================
# STEP 4 — Done
# =============================================================================

echo ""
echo "[4/4] All done."
echo ""
echo "  Deployed to:"
echo "    Primary:   https://z6fem2be13.execute-api.us-east-2.amazonaws.com/prod"
echo "    Secondary: https://jt3kw4b02f.execute-api.us-west-2.amazonaws.com/prod"
echo "    Unified:   https://api.freud.dpdns.org"
echo ""
echo "  Note: The first request after deploy will be slow (5-10s cold start)"
echo "  as transactions-api downloads the model from S3 into /tmp."
echo "  Subsequent requests will be fast."