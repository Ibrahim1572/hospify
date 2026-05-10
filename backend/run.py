"""
backend/run.py — Flask entry point
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app import db as db_module
from app import firebase as fb_module

app = create_app()

with app.app_context():
    db_module.init_app(app)
    fb_module.init_firebase(app)

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
