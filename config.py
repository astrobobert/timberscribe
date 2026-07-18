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

# GRBL controller (MKS DLC32 V2.2 running FluidNC) — g-code over WiFi.
# The controller hosts its own hotspot (FluidNC AP mode); the machine
# running this server joins it. Raw g-code rides TCP port 23 (FluidNC's
# telnet service) — the same line/ok call-response protocol as serial.
GRBL_TRANSPORT = "wifi"        # "wifi" (shop) or "serial" (USB bench fallback)
GRBL_HOST      = "192.168.0.1" # FluidNC AP-mode default address
GRBL_TCP_PORT  = 23            # FluidNC telnet service (raw g-code)
GRBL_AP_SSID   = "FluidNC"     # sled hotspot name — shown in connect errors
GRBL_CONNECT_TIMEOUT_S = 3.0   # connect/probe; fails fast when off-network
GRBL_READ_TIMEOUT_S    = 2.0   # per-read timeout while streaming
GRBL_SPINDLE_MAX_S     = 1000  # laser S-value at 100% power (must match the
                               # top of the FluidNC laser speed_map)

# USB serial bench fallback (GRBL_TRANSPORT = "serial") — the DLC32's
# USB port still works. Windows: "COM4"-style; Linux: "/dev/ttyUSB0"
# (the board's CH340 USB-UART).
SERIAL_PORT         = "COM4"
SERIAL_BAUD         = 115200   # GRBL default
GRBL_STARTUP_WAIT_S = 2.0      # serial open toggles DTR → GRBL resets; wait it out

# Motion limits
MAX_FEED_IN_PER_MIN  = 200
MIN_FEED_IN_PER_MIN  = 1
MAX_LASER_POWER_PCT  = 100
MIN_LASER_POWER_PCT  = 0
