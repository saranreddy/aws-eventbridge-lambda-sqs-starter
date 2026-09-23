#!/bin/bash
set -e

echo "======================================"
echo "EventBridge + Lambda + SQS Setup"
echo "======================================"
echo

echo "Step 1: Checking prerequisites..."
python3 scripts/doctor.py

if [ $? -ne 0 ]; then
    echo
    echo "Prerequisites check failed. Please fix issues above."
    exit 1
fi

echo
echo "Step 2: Installing Python dependencies..."
pip install -r requirements.txt

echo
echo "Step 3: Initializing Terraform..."
cd infra
terraform init

echo
echo "======================================"
echo "✓ Setup complete!"
echo "======================================"
echo
echo "Next steps:"
echo "  1. Review/customize infra/demo.tfvars"
echo "  2. terraform apply -var-file=demo.tfvars"
echo "  3. Run smoke test: make smoke"
echo
