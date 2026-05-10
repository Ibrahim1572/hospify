"""
backend/app/admissions/routes.py — uses stored procedures for admit/discharge
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required
from .. import firebase as fb

admissions_bp = Blueprint("admissions", __name__)


def _row(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@admissions_bp.get("/")
@jwt_required_custom
def list_admissions():
    status = request.args.get("status", "active")
    conn = get_db()
    with conn.cursor() as cur:
        if status == "active":
            cur.execute("SELECT * FROM active_admissions_view")
        else:
            cur.execute(
                """SELECT a.*, p.full_name AS patient_name, u.full_name AS doctor_name
                     FROM admissions a
                     JOIN patients p ON p.patient_id = a.patient_id
                     JOIN doctors  d ON d.doctor_id  = a.doctor_id
                     JOIN users    u ON u.user_id    = d.user_id
                    WHERE a.status = %s ORDER BY a.admitted_at DESC""",
                (status,)
            )
        return jsonify(_row(cur)), 200


@admissions_bp.get("/<int:aid>")
@jwt_required_custom
def get_admission(aid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT a.*, p.full_name AS patient_name, p.blood_group,
                      u.full_name AS doctor_name, d.specialization,
                      b.bed_number, w.ward_name
                 FROM admissions a
                 JOIN patients p ON p.patient_id = a.patient_id
                 JOIN doctors  d ON d.doctor_id  = a.doctor_id
                 JOIN users    u ON u.user_id    = d.user_id
                 LEFT JOIN beds  b ON b.bed_id   = a.bed_id
                 LEFT JOIN wards w ON w.ward_id  = b.ward_id
                WHERE a.admission_id = %s""",
            (aid,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        cols = [d[0] for d in cur.description]
        return jsonify(dict(zip(cols, row))), 200


@admissions_bp.post("/admit")
@roles_required("super_admin", "receptionist", "doctor")
def admit_patient():
    data = request.get_json(silent=True) or {}
    required = ["patient_id", "bed_id", "doctor_id"]
    if any(k not in data for k in required):
        return jsonify({"error": f"Required: {required}"}), 400

    conn = get_db()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CALL admit_patient(%s, %s, %s, %s)",
                (data["patient_id"], data["bed_id"], data["doctor_id"],
                 data.get("admission_type", "general"))
            )
            # get the new admission id
            cur.execute(
                "SELECT admission_id FROM admissions WHERE patient_id=%s ORDER BY admitted_at DESC LIMIT 1",
                (data["patient_id"],)
            )
            aid = cur.fetchone()[0]
        conn.commit()

        # Sync to Firebase (non-blocking)
        _sync_bed_to_firebase(data["bed_id"], "occupied")

        return jsonify({"admission_id": aid, "message": "Patient admitted"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        conn.autocommit = False


@admissions_bp.post("/<int:aid>/discharge")
@roles_required("super_admin", "doctor", "receptionist")
def discharge_patient(aid):
    user_id = int(get_jwt_identity())
    conn = get_db()
    conn.autocommit = False
    try:
        # Get bed_id before discharge
        with conn.cursor() as cur:
            cur.execute("SELECT bed_id FROM admissions WHERE admission_id=%s", (aid,))
            row = cur.fetchone()
            bed_id = row[0] if row else None
            cur.execute("CALL discharge_patient(%s, %s)", (aid, user_id))
        conn.commit()

        if bed_id:
            _sync_bed_to_firebase(bed_id, "available")

        return jsonify({"message": "Patient discharged"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        conn.autocommit = False


@admissions_bp.get("/reports/long-stay")
@roles_required("super_admin", "doctor", "nurse")
def long_stay_patients():
    """Cursor-based: patients admitted 30+ days."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            DO $$
            DECLARE
                rec RECORD;
            BEGIN
                FOR rec IN
                    SELECT admission_id, patient_id, admitted_at
                      FROM admissions
                     WHERE status = 'active'
                       AND admitted_at <= NOW() - INTERVAL '30 days'
                LOOP
                    INSERT INTO alerts(alert_type, entity_id, message)
                    VALUES ('long_stay', rec.admission_id,
                            format('Patient %s has been admitted for 30+ days (since %s)',
                                   rec.patient_id, rec.admitted_at::DATE))
                    ON CONFLICT DO NOTHING;
                END LOOP;
            END;
            $$;
            SELECT a.admission_id, p.full_name, a.admitted_at,
                   DATE_PART('day', NOW()-a.admitted_at)::INT AS days_admitted
              FROM admissions a JOIN patients p ON p.patient_id = a.patient_id
             WHERE a.status='active' AND a.admitted_at <= NOW() - INTERVAL '30 days'
             ORDER BY days_admitted DESC
            """
        )
        cols = [d[0] for d in cur.description]
        return jsonify([dict(zip(cols, r)) for r in cur.fetchall()]), 200


def _sync_bed_to_firebase(bed_id, status):
    try:
        if not fb.is_available():
            return
        db = fb.get_firestore()
        db.collection("beds").document(str(bed_id)).set(
            {"bed_id": bed_id, "status": status}, merge=True
        )
    except Exception:
        pass  # Firebase down — don't crash Postgres ops
