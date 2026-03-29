#!/bin/bash
# Clean up all GCP resources

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TERRAFORM_DIR="$(dirname "$SCRIPT_DIR")/terraform"

echo "=== Cleaning up GCP resources ==="

cd "$TERRAFORM_DIR"

if [ -f "terraform.tfstate" ]; then
    echo "Destroying GCP infrastructure..."
    tofu destroy -auto-approve
    echo "GCP resources destroyed."
else
    echo "No terraform state found. Nothing to clean up."
fi

# remove scaler state file if it exists
STATE_FILE="$(dirname "$SCRIPT_DIR")/monitor/.scaler_state"
if [ -f "$STATE_FILE" ]; then
    rm "$STATE_FILE"
    echo "Removed scaler state file."
fi

echo ""
echo "Cleanup complete!"
