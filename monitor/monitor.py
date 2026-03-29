import time
import os
import json
import subprocess
import requests

# --- config ---
CPU_THRESHOLD = 75.0
RAM_THRESHOLD = 75.0
POLL_INTERVAL = 10
COOLDOWN = 120
BREACHES_NEEDED = 3
VM_URL = "http://192.168.64.2:5000"
TERRAFORM_DIR = os.path.join(os.path.dirname(__file__), '..', 'terraform')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.scaler_state')


def get_metrics():
    try:
        r = requests.get(f"{VM_URL}/metrics", timeout=10)
        data = r.json()
        return data['cpu_percent'], data['ram_percent']
    except:
        return None, None


def gcp_is_running():
    return os.path.exists(STATE_FILE)


def scale_up():
    print("\n>>> SCALING UP: Provisioning GCP VM...")

    subprocess.run(['tofu', 'init'], cwd=TERRAFORM_DIR, capture_output=True)
    result = subprocess.run(['tofu', 'apply', '-auto-approve'], cwd=TERRAFORM_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"tofu apply failed: {result.stderr}")
        return False

    # get the GCP VM's IP
    out = subprocess.run(['tofu', 'output', '-json'], cwd=TERRAFORM_DIR, capture_output=True, text=True)
    gcp_ip = json.loads(out.stdout)['instance_ip']['value']

    # save state
    open(STATE_FILE, 'w').write(gcp_ip)
    print(f"GCP VM created at {gcp_ip}")

    # wait for flask to come up
    print("Waiting for Flask app on GCP...")
    for _ in range(20):
        try:
            if requests.get(f"http://{gcp_ip}:5000/health", timeout=5).status_code == 200:
                print(f"GCP app ready at http://{gcp_ip}:5000")
                return True
        except:
            pass
        time.sleep(10)

    print("GCP VM created but app didn't start in time")
    return True


def scale_down():
    print("\n>>> SCALING DOWN: Destroying GCP VM...")
    subprocess.run(['tofu', 'destroy', '-auto-approve'], cwd=TERRAFORM_DIR, capture_output=True)
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("GCP VM destroyed")


def main():
    print("=" * 50)
    print("VCC Assignment 3 - Resource Monitor")
    print(f"Thresholds: CPU {CPU_THRESHOLD}% | RAM {RAM_THRESHOLD}%")
    print(f"Monitoring: {VM_URL}")
    print("=" * 50)

    breach_count = 0
    normal_count = 0
    cooldown_until = 0

    while True:
        if time.time() < cooldown_until:
            print(f"[{time.strftime('%H:%M:%S')}] Cooldown ({int(cooldown_until - time.time())}s left)")
            time.sleep(POLL_INTERVAL)
            continue

        cpu, ram = get_metrics()
        if cpu is None:
            print(f"[{time.strftime('%H:%M:%S')}] Can't reach VM, retrying...")
            time.sleep(POLL_INTERVAL)
            continue

        high = cpu > CPU_THRESHOLD or ram > RAM_THRESHOLD
        print(f"[{time.strftime('%H:%M:%S')}] CPU: {cpu:.1f}% | RAM: {ram:.1f}% | {'HIGH' if high else 'OK'}")

        if high and not gcp_is_running():
            breach_count += 1
            normal_count = 0
            print(f"  -> Breach {breach_count}/{BREACHES_NEEDED}")
            if breach_count >= BREACHES_NEEDED:
                scale_up()
                breach_count = 0
                cooldown_until = time.time() + COOLDOWN

        elif not high and gcp_is_running():
            normal_count += 1
            breach_count = 0
            print(f"  -> Normal {normal_count}/{BREACHES_NEEDED} (GCP still running)")
            if normal_count >= BREACHES_NEEDED:
                scale_down()
                normal_count = 0
                cooldown_until = time.time() + COOLDOWN
        else:
            breach_count = 0
            normal_count = 0

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
