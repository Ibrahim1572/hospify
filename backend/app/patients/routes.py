"""
backend/app/patients/routes.py
"""
from flask import Blueprint, request, jsonify
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required
from . import queries as q

patients_bp = Blueprint("patients", __name__)


@patients_bp.get("/")
@jwt_required_custom
def list_patients():
    search = request.args.get("search")
    conn = get_db()
    with conn.cursor() as cur:
        data = q.get_all_patients(cur, search)
    return jsonify(data), 200


@patients_bp.get("/<int:pid>")
@jwt_required_custom
def get_patient(pid):
    conn = get_db()
    with conn.cursor() as cur:
        patient = q.get_patient_by_id(cur, pid)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404
    return jsonify(patient), 200


@patients_bp.post("/")
@roles_required("super_admin", "receptionist")
def create_patient():
    data = request.get_json(silent=True) or {}
    required = ["full_name", "dob", "gender", "cnic"]
    if any(k not in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            pid = q.create_patient(cur, data)
        conn.commit()
        return jsonify({"patient_id": pid, "message": "Patient registered"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400


@patients_bp.put("/<int:pid>")
@roles_required("super_admin", "receptionist")
def update_patient(pid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            q.update_patient(cur, pid, data)
        conn.commit()
        return jsonify({"message": "Patient updated"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400


@patients_bp.delete("/<int:pid>")
@roles_required("super_admin")
def delete_patient(pid):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            q.delete_patient(cur, pid)
        conn.commit()
        return jsonify({"message": "Patient deleted"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400


@patients_bp.get("/reports/frequent-admissions")
@roles_required("super_admin", "doctor")
def frequent_admissions():
    conn = get_db()
    with conn.cursor() as cur:
        data = q.patients_admitted_3_times_last_year(cur)
    return jsonify(data), 200
