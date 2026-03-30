import time
import os
import json
import signal
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

# GCP resource identifiers for import recovery
GCP_PROJECT = "norse-wavelet-488415-a5"
GCP_ZONE = "us-central1-a"
FIREWALL_NAME = "allow-flask-traffic"
INSTANCE_NAME = "flask-autoscale-vm"

# track active tofu subprocess so we can kill it on exit
_active_process = None


def kill_orphans():
    """Kill any leftover tofu processes before running a new one."""
    try:
        subprocess.run(['pkill', '-f', 'tofu'], capture_output=True)
    except:
        pass
    time.sleep(1)


def run_tofu(args):
    """Run a tofu command, tracking the process so Ctrl+C can clean it up."""
    global _active_process
    _active_process = subprocess.Popen(
        ['tofu'] + args,
        cwd=TERRAFORM_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = _active_process.communicate()
    returncode = _active_process.returncode
    _active_process = None
    return returncode, stdout, stderr


def cleanup_on_exit(signum, frame):
    """Handle Ctrl+C: kill any running tofu process, then exit."""
    global _active_process
    print("\nMonitor stopped.")
    if _active_process:
        print("Terminating running tofu process...")
        _active_process.terminate()
        try:
            _active_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _active_process.kill()
        _active_process = None
    if gcp_is_running():
        gcp_ip = open(STATE_FILE).read().strip()
        print(f"\n⚠ GCP VM is still running at {gcp_ip}")
        print(f"Run 'cd terraform && tofu destroy -auto-approve' to clean up.")
    raise SystemExit(0)


def import_existing_resources():
    """Import GCP resources that exist but aren't in terraform state."""
    print("Importing existing GCP resources into state...")
    firewall_id = f"projects/{GCP_PROJECT}/global/firewalls/{FIREWALL_NAME}"
    instance_id = f"projects/{GCP_PROJECT}/zones/{GCP_ZONE}/instances/{INSTANCE_NAME}"

    rc, _, err = run_tofu(['import', '-lock=false', 'google_compute_firewall.allow_flask', firewall_id])
    if rc == 0:
        print(f"  Imported firewall: {FIREWALL_NAME}")
    else:
        print(f"  Firewall import skipped: {err.strip()}")

    rc, _, err = run_tofu(['import', '-lock=false', 'google_compute_instance.flask_vm', instance_id])
    if rc == 0:
        print(f"  Imported instance: {INSTANCE_NAME}")
    else:
        print(f"  Instance import skipped: {err.strip()}")


def get_metrics():
    try:
        r = requests.get(f"{VM_URL}/metrics", timeout=10)
        data = r.json()
        return data['cpu_percent'], data['ram_percent']
    except:
        return None, None


def gcp_is_running():
    return os.path.exists(STATE_FILE)


def verify_gcp_state():
    """Check if the GCP VM is actually reachable; clean up stale state if not."""
    if not os.path.exists(STATE_FILE):
        return
    gcp_ip = open(STATE_FILE).read().strip()
    if not gcp_ip:
        os.remove(STATE_FILE)
        return
    print(f"Found existing GCP state ({gcp_ip}), verifying...")
    try:
        r = requests.get(f"http://{gcp_ip}:5000/health", timeout=10)
        if r.status_code == 200:
            print(f"GCP VM at {gcp_ip} is still running.")
            return
    except:
        pass
    print(f"GCP VM at {gcp_ip} is unreachable. Cleaning up stale state.")
    os.remove(STATE_FILE)


def scale_up():
    print("\n>>> SCALING UP: Provisioning GCP VM...")

    kill_orphans()
    run_tofu(['init'])

    returncode, stdout, stderr = run_tofu(['apply', '-auto-approve', '-lock=false'])

    # if resources already exist on GCP but state is out of sync, import and retry
    if returncode != 0 and 'alreadyExists' in stderr:
        print("GCP resources exist but state is out of sync. Auto-recovering...")
        import_existing_resources()
        # retry apply — now it will see resources in state and do a no-op or update
        returncode, stdout, stderr = run_tofu(['apply', '-auto-approve', '-lock=false'])

    if returncode != 0:
        print(f"tofu apply failed: {stderr}")
        return False

    # get the GCP VM's IP
    returncode, stdout, stderr = run_tofu(['output', '-json'])
    if returncode != 0 or not stdout.strip():
        print(f"Failed to get GCP VM IP: {stderr}")
        return False
    gcp_ip = json.loads(stdout)['instance_ip']['value']

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
    kill_orphans()
    returncode, stdout, stderr = run_tofu(['destroy', '-auto-approve', '-lock=false'])

    if returncode != 0:
        print(f"tofu destroy had issues: {stderr}")
        # if state is out of sync, import first then destroy
        if 'no matching resource' in stderr or returncode != 0:
            print("Attempting recovery: import then destroy...")
            import_existing_resources()
            run_tofu(['destroy', '-auto-approve', '-lock=false'])

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("GCP VM destroyed")


def main():
    print("=" * 50)
    print("VCC Assignment 3 - Resource Monitor")
    print(f"Thresholds: CPU {CPU_THRESHOLD}% | RAM {RAM_THRESHOLD}%")
    print(f"Monitoring: {VM_URL}")
    print("=" * 50)

    verify_gcp_state()

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
        elif high and gcp_is_running():
            breach_count = 0
            normal_count = 0
            print("  -> GCP already running, no action needed")
        else:
            breach_count = 0
            normal_count = 0

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, cleanup_on_exit)
    main()
