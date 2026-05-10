"""
backend/app/firebase.py — firebase-admin SDK initialisation
Wraps all calls in try/except so Postgres operations never fail if Firebase is down.
Uses lazy imports to avoid loading heavy dependencies on Vercel.
"""
import os
import json

_fb_app = None
_db     = None
_bucket = None
_firebase_available = False


def init_firebase(app):
    global _fb_app, _db, _bucket, _firebase_available
    
    # Check if we should skip Firebase (e.g., on Vercel to save bundle size)
    skip_firebase = os.getenv("SKIP_FIREBASE", "false").lower() == "true"
    if skip_firebase:
        app.logger.info("Firebase disabled via SKIP_FIREBASE env var")
        return
    
    creds_path   = app.config["FIREBASE_CREDENTIALS_PATH"]
    creds_json   = app.config.get("FIREBASE_CREDENTIALS_JSON", "")
    project_id   = app.config["FIREBASE_PROJECT_ID"]
    storage_bucket = app.config["FIREBASE_STORAGE_BUCKET"]

    # Try to import firebase-admin (may not be installed in slim deployments)
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage
    except ImportError:
        app.logger.warning("firebase-admin not installed — Firebase features disabled.")
        return

    cred = None
    
    # Priority 1: Use FIREBASE_CREDENTIALS_JSON env var (for Vercel deployment)
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            cred = credentials.Certificate(creds_dict)
            app.logger.info("Using Firebase credentials from FIREBASE_CREDENTIALS_JSON env var")
        except json.JSONDecodeError as e:
            app.logger.error(f"Failed to parse FIREBASE_CREDENTIALS_JSON: {e}")
            return
    # Priority 2: Use file path (for local development)
    elif os.path.exists(creds_path):
        # Check if the file is a placeholder to avoid cryptography crash
        with open(creds_path, 'r') as f:
            content = f.read()
            if "PLACEHOLDER_REPLACE_WITH_REAL_KEY" in content:
                app.logger.warning("Firebase serviceAccountKey.json is a placeholder. Firebase features disabled.")
                return
        cred = credentials.Certificate(creds_path)
        app.logger.info(f"Using Firebase credentials from file: {creds_path}")
    else:
        app.logger.warning(
            f"Firebase credentials not found (no JSON env var, no file at {creds_path}) — Firebase features disabled."
        )
        return

    try:
        _fb_app = firebase_admin.initialize_app(cred, {
            "projectId":     project_id,
            "storageBucket": storage_bucket,
        })
        _db     = firestore.client()
        _bucket = storage.bucket()
        _firebase_available = True
        app.logger.info("Firebase Admin SDK initialised")
    except Exception as e:
        app.logger.error(f"Firebase init failed: {e}")


def get_firestore():
    return _db


def get_bucket():
    return _bucket


def is_available():
    return _firebase_available
