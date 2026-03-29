import subprocess
import json
import time
import requests
import os
from config import TERRAFORM_DIR, STATE_FILE, LOCAL_APP_URL


def is_gcp_running():
    """Check if we already have a GCP instance running"""
    return os.path.exists(STATE_FILE)


def get_gcp_ip():
    """Read the GCP instance IP from state file"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return f.read().strip()
    return None


def scale_up():
    """Provision a GCP VM using OpenTofu"""
    print("\n>>> SCALING UP: Provisioning GCP VM...")

    # init terraform
    print("Running tofu init...")
    result = subprocess.run(
        ['tofu', 'init'],
        cwd=TERRAFORM_DIR,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"tofu init failed: {result.stderr}")
        return False

    # apply
    print("Running tofu apply...")
    result = subprocess.run(
        ['tofu', 'apply', '-auto-approve'],
        cwd=TERRAFORM_DIR,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"tofu apply failed: {result.stderr}")
        return False

    # get the external IP
    result = subprocess.run(
        ['tofu', 'output', '-json'],
        cwd=TERRAFORM_DIR,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Failed to get output: {result.stderr}")
        return False

    outputs = json.loads(result.stdout)
    gcp_ip = outputs['instance_ip']['value']

    # save state
    with open(STATE_FILE, 'w') as f:
        f.write(gcp_ip)

    print(f"GCP VM provisioned! IP: {gcp_ip}")

    # wait for the flask app to come up on GCP
    print("Waiting for Flask app to start on GCP...")
    gcp_url = f"http://{gcp_ip}:5000/health"
    for i in range(30):  # try for 5 minutes
        try:
            resp = requests.get(gcp_url, timeout=5)
            if resp.status_code == 200:
                print(f"GCP Flask app is ready at {gcp_url}")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(10)

    print("Warning: GCP VM created but Flask app didn't come up in time")
    return True


def scale_down():
    """Destroy the GCP VM"""
    print("\n>>> SCALING DOWN: Destroying GCP VM...")

    result = subprocess.run(
        ['tofu', 'destroy', '-auto-approve'],
        cwd=TERRAFORM_DIR,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"tofu destroy failed: {result.stderr}")
        return False

    # clean up state file
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    print("GCP VM destroyed successfully")
    return True
