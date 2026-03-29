# VCC Assignment 3: Local VM Auto-Scaling to GCP

## 1. Introduction

This project implements a local virtual machine setup with automatic scaling to Google Cloud Platform (GCP) when resource usage exceeds 75%. The system monitors CPU and RAM utilization on a local VM and dynamically provisions a cloud-based VM to handle overflow workload.

### Objective
- Create a local VM using UTM on macOS (Apple Silicon)
- Deploy a Flask web application on the local VM
- Monitor resource usage (CPU and RAM) continuously
- Auto-scale to GCP Compute Engine when usage exceeds 75%
- Scale down when usage returns to normal

## 2. System Architecture

The system consists of four main components:

1. **Local VM (UTM)**: Runs Ubuntu ARM64 with the Flask application
2. **Resource Monitor**: A Python daemon running on the host Mac that polls the VM's metrics
3. **Auto-Scaler**: Uses OpenTofu (Terraform-compatible) to provision/destroy GCP VMs
4. **GCP Compute Engine**: Cloud VM that runs the same Flask application when local resources are exhausted

See `architecture.md` for detailed diagrams.

## 3. Step-by-Step Implementation

### 3.1 Prerequisites Setup

**Tools Required:**
- macOS with Apple Silicon (M1/M2/M3/M4)
- Homebrew package manager
- GCP account with billing enabled

**Installation:**
```bash
# Run the prerequisites script
chmod +x scripts/install_prerequisites.sh
./scripts/install_prerequisites.sh
```

This installs:
- UTM (VM manager for macOS)
- Google Cloud SDK (gcloud CLI)
- OpenTofu (Infrastructure as Code, Terraform-compatible)
- Python packages (flask, psutil, requests)

**GCP Authentication:**
```bash
gcloud init
gcloud auth application-default login
```

### 3.2 Local VM Creation (UTM)

1. Download Ubuntu 22.04 LTS ARM64 Server ISO from Ubuntu's official site
2. Open UTM and create a new VM:
   - Type: Virtualize (not Emulate)
   - OS: Linux
   - Memory: 4 GB
   - CPU: 4 cores
   - Storage: 20 GB
3. Install Ubuntu with OpenSSH server enabled
4. Configure port forwarding in UTM:
   - Host:2222 -> Guest:22 (SSH)
   - Host:5000 -> Guest:5000 (Flask app)
5. Install dependencies inside the VM:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip stress-ng
pip3 install flask psutil
```

### 3.3 Flask Application Deployment

The Flask application (`app/app.py`) provides four endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page with hostname and status |
| `/health` | GET | Health check returning JSON status |
| `/metrics` | GET | CPU and RAM usage percentages |
| `/compute/<n>` | GET | CPU-intensive prime number calculation |

**Deploy to VM:**
```bash
chmod +x scripts/deploy_to_vm.sh
./scripts/deploy_to_vm.sh vcc
```

**Start the app inside the VM:**
```bash
ssh -p 2222 vcc@localhost
cd ~/app
python3 app.py
```

### 3.4 Resource Monitoring

The monitor (`monitor/monitor.py`) runs on the host Mac and:

1. Polls the VM's `/metrics` endpoint every 10 seconds
2. Checks if CPU or RAM exceeds 75%
3. Requires 3 consecutive breaches before triggering (avoids false alarms)
4. Calls the scaler to provision/destroy GCP VMs
5. Implements a 120-second cooldown after each scaling action

**Configuration** (`monitor/config.py`):
- `CPU_THRESHOLD = 75.0%`
- `RAM_THRESHOLD = 75.0%`
- `POLL_INTERVAL = 10 seconds`
- `CONSECUTIVE_BREACHES = 3`
- `COOLDOWN_PERIOD = 120 seconds`

### 3.5 GCP Auto-Scaling Configuration

**OpenTofu/Terraform Configuration** (`terraform/`):

The infrastructure is defined as code:
- `main.tf`: Defines the GCP VM (e2-medium) and firewall rules
- `variables.tf`: Configurable parameters (project ID, region, machine type)
- `outputs.tf`: Outputs the external IP after provisioning
- `startup.sh`: Bootstrap script that installs Python, deploys the Flask app, and starts it as a systemd service

**Setup:**
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your GCP project ID
```

### 3.6 Running the Demo

**Terminal 1 - Start the Flask app in the VM:**
```bash
ssh -p 2222 vcc@localhost
cd ~/app && python3 app.py
```

**Terminal 2 - Start the monitor on the host:**
```bash
cd monitor
python3 monitor.py
```

**Terminal 3 - Run the stress test:**
```bash
./scripts/stress_test.sh vcc 120
```

**Expected behavior:**
1. Monitor shows CPU/RAM readings every 10 seconds
2. When stress test starts, CPU goes above 75%
3. After 3 consecutive readings (30 seconds), auto-scaling triggers
4. OpenTofu provisions a GCP VM (takes 2-3 minutes)
5. Monitor reports the GCP VM's external IP
6. When stress test ends, CPU drops below 75%
7. After 3 normal readings, the GCP VM is destroyed

### 3.7 Cleanup

```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh
```

## 4. Results

- The monitoring system successfully detects resource usage spikes
- Auto-scaling to GCP is triggered when CPU/RAM exceeds 75% for 30+ seconds
- The same Flask application runs on both local and cloud VMs
- Scale-down occurs automatically when usage returns to normal
- The entire process is automated with no manual intervention needed

## 5. Technologies Used

| Technology | Purpose |
|-----------|---------|
| UTM | Local VM management on macOS Apple Silicon |
| Ubuntu 22.04 ARM64 | Guest OS for local VM |
| Flask | Python web framework for sample application |
| psutil | System monitoring library for CPU/RAM metrics |
| OpenTofu | Infrastructure as Code (Terraform-compatible) |
| GCP Compute Engine | Cloud VM for auto-scaling target |
| stress-ng | CPU stress testing tool |

## 6. Conclusion

This project demonstrates a practical implementation of hybrid cloud auto-scaling. The local VM handles normal workloads, and when resource usage exceeds the defined threshold, the system automatically provisions cloud resources to handle the increased demand. This approach shows how organizations can optimize costs by using local infrastructure for baseline loads while leveraging cloud elasticity for peak demands.
