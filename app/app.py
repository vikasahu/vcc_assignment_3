from flask import Flask, jsonify
import psutil
import socket
import time

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'hostname': socket.gethostname(),
        'message': 'VCC Assignment 3 - Flask App',
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
    """CPU-intensive endpoint - finds prime numbers up to n"""
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
