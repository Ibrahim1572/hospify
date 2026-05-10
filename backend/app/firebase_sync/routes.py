"""
backend/app/firebase_sync/routes.py — one-click backup push/pull
"""
from flask import Blueprint, jsonify
from ..db import get_db
from ..auth.middleware import roles_required
from .. import firebase as fb

firebase_sync_bp = Blueprint("firebase_sync", __name__)


@firebase_sync_bp.post("/backup/push")
@roles_required("super_admin")
def backup_push():
    """Push Postgres admissions, beds, patients → Firestore."""
    if not fb.is_available():
        return jsonify({"error": "Firebase not available"}), 503

    db_fs = fb.get_firestore()
    conn  = get_db()

    try:
        with conn.cursor() as cur:
            # Beds
            cur.execute("SELECT bed_id, ward_id, bed_number, bed_type, status FROM beds")
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                doc = dict(zip(cols, row))
                db_fs.collection("beds").document(str(doc["bed_id"])).set(doc)

            # Active admissions
            cur.execute(
                "SELECT admission_id, patient_id, bed_id, doctor_id, admitted_at, status "
                "FROM admissions WHERE status='active'"
            )
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                doc = dict(zip(cols, row))
                doc = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in doc.items()}
                db_fs.collection("admissions").document(str(doc["admission_id"])).set(doc)

            # Patients (summary only)
            cur.execute("SELECT patient_id, full_name, blood_group, phone FROM patients")
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                doc = dict(zip(cols, row))
                db_fs.collection("patients").document(str(doc["patient_id"])).set(doc)

        return jsonify({"message": "Postgres → Firebase sync complete"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@firebase_sync_bp.post("/backup/pull")
@roles_required("super_admin")
def backup_pull():
    """Pull Firestore beds + alerts → upsert into Postgres."""
    if not fb.is_available():
        return jsonify({"error": "Firebase not available"}), 503

    db_fs = fb.get_firestore()
    conn  = get_db()
    conn.autocommit = False
    try:
        # Pull beds
        beds_ref = db_fs.collection("beds").stream()
        with conn.cursor() as cur:
            for doc in beds_ref:
                d = doc.to_dict()
                if "bed_id" in d and "status" in d:
                    cur.execute(
                        "UPDATE beds SET status=%s WHERE bed_id=%s",
                        (d["status"], d["bed_id"])
                    )

            # Pull alerts
            alerts_ref = db_fs.collection("alerts").stream()
            for doc in alerts_ref:
                d = doc.to_dict()
                cur.execute(
                    """INSERT INTO alerts(alert_type, entity_id, message, is_resolved)
                       VALUES(%s,%s,%s,%s)
                       ON CONFLICT DO NOTHING""",
                    (d.get("alert_type", "firebase"), d.get("entity_id"),
                     d.get("message", ""), d.get("is_resolved", False))
                )
        conn.commit()
        return jsonify({"message": "Firebase → Postgres sync complete"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.autocommit = False
