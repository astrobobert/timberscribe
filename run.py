"""
TimberScribe Flask server entry point.

Run on the shop server — a plugged-in Raspberry Pi (see README /
deploy/) or any laptop on the same network as the sled:
    python run.py

Or with auto-reload during development:
    flask --app run:app run --debug --host 0.0.0.0 --port 5000

The server listens on all interfaces so a phone on the same network
can reach it at http://<server-ip>:5000. G-code goes to the sled's
DLC32 controller over WiFi (see config.py GRBL_* settings).
"""

from app import create_app
import config

app = create_app()

if __name__ == "__main__":
    print(f"\nTimber Scribe server starting on http://0.0.0.0:{config.FLASK_PORT}")
    print(f"Upload folder : {config.UPLOAD_DIR}")
    print(f"Database      : {config.DB_PATH}\n")
    app.run(
        host  = config.FLASK_HOST,
        port  = config.FLASK_PORT,
        debug = False,          # set True during development
    )
