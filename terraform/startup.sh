#!/bin/bash
set -e
exec > /var/log/startup-script.log 2>&1

echo "=== Starting Flask app deployment ==="

apt-get update
apt-get install -y python3 python3-pip python3-venv

mkdir -p /opt/flask-app
cd /opt/flask-app

# write the flask app
cat > app.py << 'APPEOF'
from flask import Flask, jsonify
import psutil
import socket
import time

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'hostname': socket.gethostname(),
        'message': 'VCC Assignment 3 - Flask App (GCP)',
        'status': 'running'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'hostname': socket.gethostname(),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/metrics')
def metrics():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    return jsonify({
        'cpu_percent': cpu,
        'ram_percent': ram,
        'hostname': socket.gethostname()
    })

@app.route('/compute/<int:n>')
def compute(n):
    start = time.time()
    primes = []
    for num in range(2, n):
        is_prime = True
        for i in range(2, int(num**0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    elapsed = time.time() - start
    return jsonify({
        'primes_found': len(primes),
        'range': n,
        'time_seconds': round(elapsed, 3),
        'hostname': socket.gethostname()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
APPEOF

cat > requirements.txt << 'REQEOF'
flask==2.3.3
psutil==5.9.8
REQEOF

pip3 install -r requirements.txt

# create a systemd service so flask runs on boot
cat > /etc/systemd/system/flask-app.service << 'SVCEOF'
[Unit]
Description=Flask App
After=network.target

[Service]
User=root
WorkingDirectory=/opt/flask-app
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable flask-app
systemctl start flask-app

echo "=== Flask app deployed and running ==="
