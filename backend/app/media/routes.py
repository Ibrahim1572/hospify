"""
backend/app/media/routes.py — dual storage: Postgres BYTEA + Firebase Storage
"""
import os, io, base64
from flask import Blueprint, request, jsonify, send_file
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required
from .. import firebase as fb
from flask import current_app

media_bp = Blueprint("media", __name__)

MAX_SIZE = 10 * 1024 * 1024  # 10 MB


@media_bp.post("/upload")
@jwt_required_custom
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    entity_type = request.form.get("entity_type", "general")
    entity_id   = request.form.get("entity_id")
    uploaded_by = request.form.get("uploaded_by")

    data_bytes = f.read()
    if len(data_bytes) > MAX_SIZE:
        return jsonify({"error": "File exceeds 10 MB limit"}), 413

    file_type = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "bin"
    firebase_url = None

    # Upload to Firebase Storage (optional)
    try:
        if fb.is_available() and entity_id:
            bucket = fb.get_bucket()
            blob_path = f"{entity_type}/{entity_id}/{f.filename}"
            blob = bucket.blob(blob_path)
            blob.upload_from_string(data_bytes, content_type=f.content_type)
            blob.make_public()
            firebase_url = blob.public_url
    except Exception as e:
        current_app.logger.warning(f"Firebase upload failed: {e}")

    # Store BYTEA in Postgres
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO media_files(entity_type,entity_id,file_name,file_type,
                            file_data,firebase_url,uploaded_by)
                   VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING file_id""",
                (entity_type, entity_id, f.filename, file_type,
                 psycopg2_bytes(data_bytes), firebase_url, uploaded_by)
            )
            fid = cur.fetchone()[0]
        conn.commit()
        return jsonify({"file_id": fid, "firebase_url": firebase_url}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


def psycopg2_bytes(b):
    import psycopg2
    return psycopg2.Binary(b)


@media_bp.get("/<int:file_id>")
@jwt_required_custom
def download_file(file_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT file_name, file_type, file_data, firebase_url FROM media_files WHERE file_id=%s",
            (file_id,)
        )
        row = cur.fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404

    fname, ftype, fdata, fb_url = row

    # If Firebase URL exists, redirect there; else serve from Postgres
    if fb_url:
        return jsonify({"firebase_url": fb_url, "file_name": fname}), 200

    mime_map = {"jpeg": "image/jpeg", "jpg": "image/jpeg",
                "png": "image/png", "pdf": "application/pdf"}
    mime = mime_map.get(ftype, "application/octet-stream")
    return send_file(io.BytesIO(bytes(fdata)), mimetype=mime,
                     download_name=fname, as_attachment=False)


@media_bp.get("/entity/<string:entity_type>/<int:entity_id>")
@jwt_required_custom
def list_entity_files(entity_type, entity_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT file_id,file_name,file_type,firebase_url,uploaded_at "
            "FROM media_files WHERE entity_type=%s AND entity_id=%s ORDER BY uploaded_at DESC",
            (entity_type, entity_id)
        )
        cols = [d[0] for d in cur.description]
        return jsonify([dict(zip(cols, r)) for r in cur.fetchall()]), 200
