#!/bin/bash
# Stress test the local VM to trigger auto-scaling

VM_USER="${1:-vks}"
VM_HOST="192.168.64.2"
DURATION="${2:-120}"

echo "==========================================="
echo "  Stress Test - VCC Assignment 3"
echo "==========================================="
echo ""
echo "This will push CPU usage above 75% on the local VM"
echo "to trigger the auto-scaling mechanism."
echo ""

echo "Method 1: Using stress-ng (recommended)"
echo "Running stress-ng on the VM for ${DURATION} seconds..."
echo ""

ssh ${VM_USER}@${VM_HOST} "stress-ng --cpu 4 --timeout ${DURATION}s --metrics-brief"

echo ""
echo "Stress test complete!"
echo ""
echo "---"
echo "Alternative: You can also use the compute endpoint:"
echo "  curl http://${VM_HOST}:5000/compute/1000000"
