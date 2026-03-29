#!/bin/bash
# Deploy Flask app to the local UTM VM via SCP

VM_USER="${1:-vks}"
VM_HOST="192.168.64.2"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Deploying Flask app to local VM..."
echo "VM: ${VM_USER}@${VM_HOST}"

# copy app files to VM
scp -r "$PROJECT_DIR/app/" ${VM_USER}@${VM_HOST}:~/

echo ""
echo "Files deployed! Now SSH into the VM and start the app:"
echo "  ssh ${VM_USER}@${VM_HOST}"
echo "  cd ~/app"
echo "  pip3 install -r requirements.txt"
echo "  python3 app.py"
