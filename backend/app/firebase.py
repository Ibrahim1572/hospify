"""
backend/app/firebase.py — firebase-admin SDK initialisation
Wraps all calls in try/except so Postgres operations never fail if Firebase is down.
"""
import os
import firebase_admin
from firebase_admin import credentials, firestore, storage
from flask import current_app

_fb_app = None
_db     = None
_bucket = None


def init_firebase(app):
    global _fb_app, _db, _bucket
    creds_path   = app.config["FIREBASE_CREDENTIALS_PATH"]
    project_id   = app.config["FIREBASE_PROJECT_ID"]
    storage_bucket = app.config["FIREBASE_STORAGE_BUCKET"]

    if not os.path.exists(creds_path):
        app.logger.warning(
            f"Firebase credentials not found at {creds_path} — Firebase features disabled."
        )
        return

    # Check if the file is a placeholder to avoid cryptography crash
    with open(creds_path, 'r') as f:
        content = f.read()
        if "PLACEHOLDER_REPLACE_WITH_REAL_KEY" in content:
            app.logger.warning("Firebase serviceAccountKey.json is a placeholder. Firebase features disabled.")
            return

    try:
        cred = credentials.Certificate(creds_path)
        _fb_app = firebase_admin.initialize_app(cred, {
            "projectId":     project_id,
            "storageBucket": storage_bucket,
        })
        _db     = firestore.client()
        _bucket = storage.bucket()
        app.logger.info("Firebase Admin SDK initialised")
    except Exception as e:
        app.logger.error(f"Firebase init failed: {e}")


def get_firestore():
    return _db


def get_bucket():
    return _bucket


def is_available():
    return _db is not None
