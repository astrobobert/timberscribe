"""
TimberScribe Flask server entry point.

Run on the Pi:
    python run.py

Or with auto-reload during development:
    flask --app run:app run --debug --host 0.0.0.0 --port 5000

The server listens on all interfaces so phones and laptops on the
same WiFi network (or hotspot) can reach it at http://<pi-ip>:5000
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
