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

# GRBL controller (MKS DLC32 V2.1) — g-code over USB serial.
# The DLC32's CH340 USB-UART enumerates as /dev/ttyUSB0 on the Pi.
SERIAL_PORT         = "/dev/ttyUSB0"
SERIAL_BAUD         = 115200   # GRBL default
SERIAL_TIMEOUT_S    = 2.0      # per-read timeout
GRBL_STARTUP_WAIT_S = 2.0      # GRBL resets on port open; wait for its banner
GRBL_SPINDLE_MAX_S  = 1000     # laser S-value at 100% power (must match GRBL $30)

# Motion limits
MAX_FEED_IN_PER_MIN  = 200
MIN_FEED_IN_PER_MIN  = 1
MAX_LASER_POWER_PCT  = 100
MIN_LASER_POWER_PCT  = 0
