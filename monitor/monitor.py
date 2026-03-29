import time
import requests
import sys
import os

# add parent dir so we can import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    CPU_THRESHOLD, RAM_THRESHOLD, POLL_INTERVAL,
    COOLDOWN_PERIOD, CONSECUTIVE_BREACHES, LOCAL_APP_URL
)
from scaler import scale_up, scale_down, is_gcp_running


def get_metrics():
    """Fetch CPU and RAM metrics from the local VM's Flask app"""
    try:
        resp = requests.get(f"{LOCAL_APP_URL}/metrics", timeout=10)
        data = resp.json()
        return data['cpu_percent'], data['ram_percent']
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return None, None


def main():
    print("=" * 60)
    print("VCC Assignment 3 - Resource Monitor")
    print(f"CPU Threshold: {CPU_THRESHOLD}%")
    print(f"RAM Threshold: {RAM_THRESHOLD}%")
    print(f"Poll Interval: {POLL_INTERVAL}s")
    print(f"Consecutive Breaches needed: {CONSECUTIVE_BREACHES}")
    print(f"Monitoring: {LOCAL_APP_URL}")
    print("=" * 60)

    breach_count = 0
    normal_count = 0
    cooldown_until = 0

    while True:
        now = time.time()

        # check if we're in cooldown
        if now < cooldown_until:
            remaining = int(cooldown_until - now)
            print(f"[{time.strftime('%H:%M:%S')}] Cooldown active ({remaining}s remaining)")
            time.sleep(POLL_INTERVAL)
            continue

        cpu, ram = get_metrics()

        if cpu is None:
            print(f"[{time.strftime('%H:%M:%S')}] Could not fetch metrics, retrying...")
            time.sleep(POLL_INTERVAL)
            continue

        threshold_exceeded = cpu > CPU_THRESHOLD or ram > RAM_THRESHOLD
        status = "HIGH" if threshold_exceeded else "OK"

        print(f"[{time.strftime('%H:%M:%S')}] CPU: {cpu:.1f}% | RAM: {ram:.1f}% | Status: {status}")

        if threshold_exceeded and not is_gcp_running():
            breach_count += 1
            normal_count = 0
            print(f"  -> Breach {breach_count}/{CONSECUTIVE_BREACHES}")

            if breach_count >= CONSECUTIVE_BREACHES:
                print(f"\n{'!' * 60}")
                print(f"THRESHOLD EXCEEDED for {CONSECUTIVE_BREACHES} consecutive checks!")
                print(f"CPU: {cpu:.1f}% | RAM: {ram:.1f}%")
                print(f"{'!' * 60}")

                success = scale_up()
                if success:
                    print("Auto-scaling complete!")
                else:
                    print("Auto-scaling failed!")

                breach_count = 0
                cooldown_until = time.time() + COOLDOWN_PERIOD

        elif not threshold_exceeded and is_gcp_running():
            normal_count += 1
            breach_count = 0
            print(f"  -> Normal {normal_count}/{CONSECUTIVE_BREACHES} (GCP still running)")

            if normal_count >= CONSECUTIVE_BREACHES:
                print(f"\nUsage back to normal for {CONSECUTIVE_BREACHES} consecutive checks")
                scale_down()
                normal_count = 0
                cooldown_until = time.time() + COOLDOWN_PERIOD

        else:
            # reset counters if pattern breaks
            if not threshold_exceeded:
                breach_count = 0
            if threshold_exceeded:
                normal_count = 0

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
