"""
backend/app/admin/routes.py — user management (super_admin only)
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from ..db import get_db
from ..auth.middleware import roles_required

admin_bp = Blueprint("admin", __name__)

def _row(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@admin_bp.get("/users")
@roles_required("super_admin")
def list_users():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT user_id, full_name, email, role, is_active, created_at FROM users ORDER BY created_at DESC"
        )
        return jsonify(_row(cur)), 200


@admin_bp.post("/users")
@roles_required("super_admin")
def create_user():
    data = request.get_json(silent=True) or {}
    required = ["full_name", "email", "password", "role"]
    if any(k not in data for k in required):
        return jsonify({"error": f"Required: {required}"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users(full_name,email,password_hash,role) VALUES(%s,%s,%s,%s) RETURNING user_id",
                (data["full_name"], data["email"].lower().strip(),
                 generate_password_hash(data["password"]), data["role"])
            )
            uid = cur.fetchone()[0]
        conn.commit()
        return jsonify({"user_id": uid}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@admin_bp.patch("/users/<int:uid>/status")
@roles_required("super_admin")
def toggle_user_status(uid):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_active = NOT is_active WHERE user_id=%s RETURNING is_active",
                (uid,)
            )
            row = cur.fetchone()
        conn.commit()
        return jsonify({"is_active": row[0]}), 200
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@admin_bp.get("/audit-log")
@roles_required("super_admin")
def audit_log():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT al.*, u.full_name AS user_name
                 FROM audit_log al
                 LEFT JOIN users u ON u.user_id = al.user_id
                ORDER BY al.timestamp DESC LIMIT 200"""
        )
        return jsonify(_row(cur)), 200


@admin_bp.get("/alerts")
@roles_required("super_admin", "nurse", "pharmacist")
def list_alerts():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM alerts WHERE is_resolved=FALSE ORDER BY created_at DESC"
        )
        return jsonify(_row(cur)), 200


@admin_bp.patch("/alerts/<int:alert_id>/resolve")
@roles_required("super_admin", "nurse", "pharmacist")
def resolve_alert(alert_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE alerts SET is_resolved=TRUE WHERE alert_id=%s", (alert_id,))
        conn.commit()
        return jsonify({"message": "Alert resolved"}), 200
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400
