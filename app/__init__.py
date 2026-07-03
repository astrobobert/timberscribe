"""
Flask application factory.
"""

import os
from flask import Flask

import config
from app import job_store


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder = "../templates",
        static_folder   = "../static",
    )

    app.config["SECRET_KEY"]       = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_BYTES

    # Ensure required directories exist
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    os.makedirs(config.DATA_DIR,   exist_ok=True)

    # Initialise database
    job_store.init_db()

    # Register routes
    from app.routes import bp
    app.register_blueprint(bp)

    return app
