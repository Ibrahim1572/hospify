"""
backend/app/nurses/routes.py — vitals logging
"""
from flask import Blueprint, request, jsonify
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required

nurses_bp = Blueprint("nurses", __name__)

def _row(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@nurses_bp.get("/")
@jwt_required_custom
def list_nurses():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT n.nurse_id, u.full_name, u.email, n.shift, w.ward_name
                 FROM nurses n
                 JOIN users u ON u.user_id = n.user_id
                 LEFT JOIN wards w ON w.ward_id = n.ward_id
                ORDER BY u.full_name"""
        )
        return jsonify(_row(cur)), 200


# ── VITALS ─────────────────────────────────────────────────────────────────

@nurses_bp.get("/vitals/<int:admission_id>")
@jwt_required_custom
def get_vitals(admission_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT v.*, u.full_name AS nurse_name
                 FROM vitals v
                 LEFT JOIN nurses n ON n.nurse_id = v.nurse_id
                 LEFT JOIN users  u ON u.user_id  = n.user_id
                WHERE v.admission_id = %s
                ORDER BY v.recorded_at DESC""",
            (admission_id,)
        )
        return jsonify(_row(cur)), 200


@nurses_bp.post("/vitals")
@roles_required("super_admin", "nurse")
def log_vitals():
    data = request.get_json(silent=True) or {}
    if "admission_id" not in data:
        return jsonify({"error": "admission_id required"}), 400
    conn = get_db()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO vitals(admission_id, nurse_id, temperature,
                       blood_pressure_sys, blood_pressure_dia, pulse,
                       oxygen_saturation, weight, notes)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING vital_id""",
                (
                    data["admission_id"], data.get("nurse_id"),
                    data.get("temperature"), data.get("blood_pressure_sys"),
                    data.get("blood_pressure_dia"), data.get("pulse"),
                    data.get("oxygen_saturation"), data.get("weight"),
                    data.get("notes")
                )
            )
            vid = cur.fetchone()[0]
        conn.commit()
        return jsonify({"vital_id": vid, "message": "Vitals logged"}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400
    finally:
        conn.autocommit = False


@nurses_bp.get("/vitals/<int:admission_id>/averages")
@jwt_required_custom
def vital_averages(admission_id):
    """Uses average_vital() SQL function for each vital sign."""
    conn = get_db()
    with conn.cursor() as cur:
        result = {}
        for vital in ["temperature", "blood_pressure_sys", "blood_pressure_dia",
                       "pulse", "oxygen_saturation", "weight"]:
            cur.execute(
                "SELECT average_vital(%s, %s)", (admission_id, vital)
            )
            result[vital] = float(cur.fetchone()[0] or 0)
    return jsonify(result), 200


@nurses_bp.get("/alerts/no-vitals")
@roles_required("super_admin", "nurse", "doctor")
def no_vitals_alert():
    """Admissions with no vitals in last 12 hours (subquery demo)."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.admission_id, p.full_name AS patient_name, w.ward_name, b.bed_number
              FROM admissions a
              JOIN patients p ON p.patient_id = a.patient_id
              LEFT JOIN beds  b ON b.bed_id  = a.bed_id
              LEFT JOIN wards w ON w.ward_id = b.ward_id
             WHERE a.status = 'active'
               AND a.admission_id NOT IN (
                   SELECT DISTINCT admission_id FROM vitals
                    WHERE recorded_at >= NOW() - INTERVAL '12 hours'
               )
             ORDER BY a.admitted_at
            """
        )
        cols = [d[0] for d in cur.description]
        return jsonify([dict(zip(cols, r)) for r in cur.fetchall()]), 200
