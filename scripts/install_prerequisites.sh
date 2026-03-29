#!/bin/bash
# Install all required tools for VCC Assignment 3

set -e

echo "=== Installing UTM (Virtual Machine Manager) ==="
brew install --cask utm

echo ""
echo "=== Installing Google Cloud SDK ==="
brew install --cask google-cloud-sdk

echo ""
echo "=== Installing OpenTofu (Terraform alternative) ==="
brew install opentofu

echo ""
echo "=== Installing Python dependencies ==="
pip3 install flask psutil requests

echo ""
echo "==========================================="
echo "Installation complete!"
echo ""
echo "Next steps (run these manually):"
echo "  1. gcloud init"
echo "  2. gcloud auth application-default login"
echo "  3. Copy terraform/terraform.tfvars.example to terraform/terraform.tfvars"
echo "  4. Edit terraform/terraform.tfvars with your GCP project ID"
echo "==========================================="
