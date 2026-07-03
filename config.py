"""
TimberScribe Flask server configuration.
All paths, ports, and default burn settings live here.
"""

import os

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DATA_DIR   = os.path.join(BASE_DIR, "data")
DB_PATH    = os.path.join(DATA_DIR, "jobs.db")

# Flask
FLASK_HOST = "0.0.0.0"   # listen on all interfaces (WiFi hotspot)
FLASK_PORT = 5000
SECRET_KEY = "timberscribe-dev-key"   # change for production

# File limits
MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 10 MB — .tsj files are tiny

# Default burn settings (user-adjustable from UI before each print)
DEFAULT_FEED_IN_PER_MIN  = 32    # inches per minute
DEFAULT_LASER_POWER_PCT  = 70    # percent
DEFAULT_TRAVEL_IN_PER_MIN = 118  # laser-off travel speed

# Hardware GPIO pins (Pi 4/5, BCM numbering)
MOTOR_PWM_PIN    = 18   # motor speed PWM
MOTOR_DIR_PIN    = 23   # motor direction
MOTOR_ENC_A_PIN  = 24   # encoder channel A
MOTOR_ENC_B_PIN  = 25   # encoder channel B
LASER_PWM_PIN    = 12   # laser power PWM (hardware PWM)
TAPE_SENSOR_PIN  = 17   # optical tape sensor input

# Motion limits
MAX_FEED_IN_PER_MIN  = 200
MIN_FEED_IN_PER_MIN  = 1
MAX_LASER_POWER_PCT  = 100
MIN_LASER_POWER_PCT  = 0
