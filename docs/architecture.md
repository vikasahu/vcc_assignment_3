# Architecture Design

## System Architecture Diagram

```
+------------------------------------------------------------------+
|                        HOST MAC (Apple Silicon)                   |
|                                                                  |
|   +--------------------+        +---------------------------+    |
|   |   monitor.py       |        |    OpenTofu (Terraform)   |    |
|   |   (Python daemon)  |------->|    Infrastructure as Code |    |
|   |                    |        |                           |    |
|   |  - Polls /metrics  |        |  - tofu init              |    |
|   |  - Tracks CPU/RAM  |        |  - tofu apply             |    |
|   |  - Breach counter  |        |  - tofu destroy           |    |
|   +--------+-----------+        +-------------+-------------+    |
|            |                                  |                  |
|            | HTTP GET /metrics                | Provisions/      |
|            | (every 10 seconds)               | Destroys         |
|            v                                  v                  |
|   +--------------------+        +---------------------------+    |
|   |   LOCAL VM (UTM)   |        |    GCP COMPUTE ENGINE     |    |
|   |   Ubuntu ARM64     |        |    Ubuntu x86_64          |    |
|   |                    |        |                           |    |
|   |  +---------------+ |        |  +----------------------+ |    |
|   |  | Flask App     | |        |  | Flask App            | |    |
|   |  | Port 5000     | |        |  | Port 5000            | |    |
|   |  |               | |        |  |                      | |    |
|   |  | Endpoints:    | |        |  | Same app deployed    | |    |
|   |  | /             | |        |  | via startup script   | |    |
|   |  | /health       | |        |  |                      | |    |
|   |  | /metrics      | |        |  | Runs as systemd      | |    |
|   |  | /compute/<n>  | |        |  | service               | |    |
|   |  +---------------+ |        |  +----------------------+ |    |
|   +--------------------+        +---------------------------+    |
|                                                                  |
|   +----------------------------------------------------------+   |
|   |               Stress Testing Tools                       |   |
|   |  stress-ng (inside VM) | curl /compute/<n> (from host)   |   |
|   +----------------------------------------------------------+   |
+------------------------------------------------------------------+
```

## Auto-Scaling Flow

```
                    Start
                      |
                      v
            +-------------------+
            | Poll /metrics     |
            | (every 10 sec)    |
            +--------+----------+
                     |
                     v
            +-------------------+
            | CPU > 75% OR      |
            | RAM > 75%?        |
            +--------+----------+
                     |
              Yes    |    No
              |      |      |
              v      |      v
     +------------+  | +------------------+
     | Increment  |  | | Reset breach     |
     | breach     |  | | counter          |
     | counter    |  | |                  |
     +-----+------+  | | Is GCP running   |
           |         | | AND normal for   |
           v         | | 3 checks?        |
     +------------+  | +--------+---------+
     | Breaches   |  |          |
     | >= 3?      |  |     Yes  |  No
     +-----+------+  |      |   |   |
           |         |      v   |   v
      Yes  |  No     | +--------+ | Continue
       |   |   |     | | Scale  | | monitoring
       v   |   v     | | Down   | |
  +--------+ | Cont. | +--------+ |
  | Scale  | |       |            |
  | Up     | |       |            |
  | (GCP)  | |       |            |
  +--------+ |       |            |
       |      |       |            |
       v      v       v            v
  +-----------------------------------------+
  | Enter cooldown (120 seconds)            |
  | Then resume monitoring                  |
  +-----------------------------------------+
```

## Component Description

| Component | Location | Purpose |
|-----------|----------|---------|
| Flask App | Local VM + GCP | Web application that serves requests and exposes metrics |
| Monitor | Host Mac | Polls metrics, makes scaling decisions |
| Scaler | Host Mac | Executes OpenTofu commands to provision/destroy GCP VMs |
| OpenTofu | Host Mac | Infrastructure as Code tool for GCP resource management |
| stress-ng | Local VM | Generates CPU load for testing the auto-scaling trigger |

## Network Configuration

- **Local VM**: NAT mode with port forwarding
  - Host port 2222 -> Guest port 22 (SSH)
  - Host port 5000 -> Guest port 5000 (Flask)
- **GCP VM**: External IP with firewall rules
  - Port 5000 open for Flask
  - Port 22 open for SSH
