#!/bin/bash
set -e

BASE="$(dirname "$0")/packages"
PLATFORM="manylinux2014_x86_64"
PYTHON_VERSION="3.12"

packages=(
  "accounts_lambda_package"
  "transactions_lambda_package"
  "fraud_alert_lambda_package"
  "twilio_webhook_lambda_package"
)

for pkg in "${packages[@]}"; do
  echo "Installing dependencies for $pkg..."
  pip install \
    -r "$BASE/$pkg/requirements.txt" \
    --target "$BASE/$pkg" \
    --platform $PLATFORM \
    --python-version $PYTHON_VERSION \
    --only-binary=:all: \
    --upgrade
  echo "Removing boto3/botocore from $pkg..."
  rm -rf "$BASE/$pkg/boto3" "$BASE/$pkg/botocore"
  echo "Done: $pkg"
done

echo ""
echo "All packages installed. Now handle onnxruntime manually for transactions:"
echo "  pip download onnxruntime --dest /tmp/onnx --platform manylinux_2_27_x86_64 --python-version 3.12 --only-binary=:all: --no-deps"
echo "  unzip -o /tmp/onnx/onnxruntime*.whl -d $BASE/transactions_lambda_package"
echo ""
echo "Then zip each package:"
echo "  cd $BASE/accounts_lambda_package && zip -r ../../zip/accounts_lambda_package.zip ."
echo "  cd $BASE/transactions_lambda_package && zip -r ../../zip/transactions_lambda_package.zip ."
echo "  cd $BASE/fraud_alert_lambda_package && zip -r ../../zip/fraud_alert_lambda_package.zip ."
echo "  cd $BASE/twilio_webhook_lambda_package && zip -r ../../zip/twilio_webhook_lambda_package.zip ."