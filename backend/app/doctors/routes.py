"""
backend/app/doctors/routes.py
"""
from flask import Blueprint, request, jsonify
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required

doctors_bp = Blueprint("doctors", __name__)

def _row(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@doctors_bp.get("/")
@jwt_required_custom
def list_doctors():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT d.doctor_id, u.full_name, u.email, d.specialization,
                      d.qualification, d.phone, d.available_days, u.is_active
                 FROM doctors d JOIN users u ON u.user_id = d.user_id
                ORDER BY u.full_name"""
        )
        return jsonify(_row(cur)), 200


@doctors_bp.get("/<int:did>")
@jwt_required_custom
def get_doctor(did):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT d.*, u.full_name, u.email, u.is_active
                 FROM doctors d JOIN users u ON u.user_id = d.user_id
                WHERE d.doctor_id=%s""",
            (did,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        cols = [d[0] for d in cur.description]
        return jsonify(dict(zip(cols, row))), 200


@doctors_bp.get("/<int:did>/schedule")
@jwt_required_custom
def doctor_schedule(did):
    """Today's appointments for a doctor (uses doctor_schedule_today view)."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM doctor_schedule_today WHERE doctor_id=%s", (did,))
        row = cur.fetchone()
        if not row:
            return jsonify({}), 200
        cols = [d[0] for d in cur.description]
        return jsonify(dict(zip(cols, row))), 200


# ── APPOINTMENTS ───────────────────────────────────────────────────────────

@doctors_bp.get("/appointments/all")
@jwt_required_custom
def list_all_appointments():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT ap.*, p.full_name AS patient_name, p.phone AS patient_phone,
                      u.full_name AS doctor_name
                 FROM appointments ap
                 JOIN patients p ON p.patient_id = ap.patient_id
                 JOIN doctors d ON d.doctor_id = ap.doctor_id
                 JOIN users u ON u.user_id = d.user_id
                ORDER BY ap.scheduled_at DESC"""
        )
        return jsonify(_row(cur)), 200


@doctors_bp.get("/<int:did>/appointments")
@jwt_required_custom
def list_appointments(did):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT ap.*, p.full_name AS patient_name, p.phone AS patient_phone
                 FROM appointments ap
                 JOIN patients p ON p.patient_id = ap.patient_id
                WHERE ap.doctor_id=%s ORDER BY ap.scheduled_at DESC""",
            (did,)
        )
        return jsonify(_row(cur)), 200


@doctors_bp.post("/appointments")
@roles_required("super_admin", "receptionist")
def create_appointment():
    data = request.get_json(silent=True) or {}
    required = ["patient_id", "doctor_id", "scheduled_at"]
    if any(k not in data for k in required):
        return jsonify({"error": f"Required: {required}"}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO appointments(patient_id,doctor_id,scheduled_at,reason) "
                "VALUES(%s,%s,%s,%s) RETURNING appointment_id",
                (data["patient_id"], data["doctor_id"], data["scheduled_at"], data.get("reason"))
            )
            aid = cur.fetchone()[0]
        conn.commit()
        return jsonify({"appointment_id": aid}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@doctors_bp.patch("/appointments/<int:apid>/status")
@roles_required("super_admin", "receptionist", "doctor")
def update_appointment_status(apid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("scheduled", "completed", "cancelled", "no_show"):
        return jsonify({"error": "Invalid status"}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE appointments SET status=%s WHERE appointment_id=%s", (status, apid))
        conn.commit()
        return jsonify({"message": "Updated"}), 200
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400
