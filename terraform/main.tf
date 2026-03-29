terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  credentials = file("${path.module}/credentials.json")
  project     = var.project_id
  region      = var.region
  zone        = var.zone
}

# firewall rule to allow flask traffic and ssh
resource "google_compute_firewall" "allow_flask" {
  name    = "allow-flask-traffic"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["5000", "22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["flask-server"]
}

# the GCP VM that runs our flask app when local VM is overloaded
resource "google_compute_instance" "flask_vm" {
  name         = "flask-autoscale-vm"
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["flask-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
    }
  }

  network_interface {
    network = "default"
    access_config {
      # gives the VM an external IP
    }
  }

  metadata_startup_script = file("${path.module}/startup.sh")
}
