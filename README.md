# VCC Assignment 3 - Local VM Auto-Scaling to GCP

Auto-scale a local VM to Google Cloud Platform when resource usage exceeds 75%.

## How It Works

1. A Flask web app runs on a local UTM VM (Ubuntu ARM64)
2. A Python monitor on the host checks CPU/RAM every 10 seconds
3. If usage stays above 75% for 3 consecutive checks, it provisions a GCP VM using OpenTofu
4. When usage drops back to normal, the GCP VM is destroyed

## Project Structure

```
├── app/                  # Flask web application
│   ├── app.py
│   └── requirements.txt
├── monitor/              # Resource monitoring daemon
│   ├── monitor.py        # Main monitor script
│   ├── config.py         # Thresholds and settings
│   └── scaler.py         # Auto-scaling logic
├── terraform/            # GCP infrastructure config
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── startup.sh
│   └── terraform.tfvars.example
├── scripts/              # Helper scripts
│   ├── install_prerequisites.sh
│   ├── setup_local_vm.sh
│   ├── deploy_to_vm.sh
│   ├── stress_test.sh
│   └── cleanup.sh
└── docs/                 # Documentation
    ├── report.md
    └── architecture.md
```

## Quick Start

### 1. Install prerequisites
```bash
chmod +x scripts/install_prerequisites.sh
./scripts/install_prerequisites.sh
```

### 2. Set up GCP
```bash
gcloud init
gcloud auth application-default login
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your GCP project ID
```

### 3. Set up the local VM
```bash
./scripts/setup_local_vm.sh   # Follow the printed instructions
./scripts/deploy_to_vm.sh vcc  # Deploy app to VM
```

### 4. Start the Flask app (inside the VM)
```bash
ssh -p 2222 vcc@localhost
cd ~/app && python3 app.py
```

### 5. Start the monitor (on host Mac)
```bash
cd monitor
python3 monitor.py
```

### 6. Trigger auto-scaling (stress test)
```bash
./scripts/stress_test.sh vcc 120
```

### 7. Cleanup
```bash
./scripts/cleanup.sh
```

## Configuration

Edit `monitor/config.py` to adjust:
- `CPU_THRESHOLD` - CPU usage threshold (default: 75%)
- `RAM_THRESHOLD` - RAM usage threshold (default: 75%)
- `POLL_INTERVAL` - Check interval in seconds (default: 10)
- `CONSECUTIVE_BREACHES` - Readings above threshold before scaling (default: 3)
- `COOLDOWN_PERIOD` - Wait time after scaling action (default: 120s)

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Homebrew
- GCP account with billing enabled
- Python 3
