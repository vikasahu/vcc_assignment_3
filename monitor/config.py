import os

# thresholds
CPU_THRESHOLD = 75.0
RAM_THRESHOLD = 75.0

# how often to check (seconds)
POLL_INTERVAL = 10

# wait this long after scaling before checking again
COOLDOWN_PERIOD = 120

# need this many consecutive readings above threshold before scaling
CONSECUTIVE_BREACHES = 3

# where the flask app is running (local VM direct IP via Apple Virtualization)
LOCAL_APP_URL = "http://192.168.64.2:5000"

# terraform directory
TERRAFORM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'terraform')

# state file to track if GCP instance is running
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.scaler_state')
