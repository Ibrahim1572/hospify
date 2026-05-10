"""
backend/app/wards/routes.py — Wards + Beds
"""
from flask import Blueprint, request, jsonify
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required

wards_bp = Blueprint("wards", __name__)


def _row(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ── WARDS ──────────────────────────────────────────────────────────────────

@wards_bp.get("/")
@jwt_required_custom
def list_wards():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT w.ward_id, w.ward_name, w.ward_type, w.floor_number, w.total_beds,
                      COALESCE(
                          json_agg(json_build_object(
                              'bed_id', b.bed_id, 'bed_number', b.bed_number, 
                              'bed_type', b.bed_type, 'status', b.status
                          ) ORDER BY b.bed_number) FILTER (WHERE b.bed_id IS NOT NULL), '[]'::json
                      ) AS beds
                 FROM wards w
                 LEFT JOIN beds b ON b.ward_id = w.ward_id
                GROUP BY w.ward_id
                ORDER BY w.ward_name"""
        )
        return jsonify(_row(cur)), 200


@wards_bp.post("/")
@roles_required("super_admin")
def create_ward():
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO wards(ward_name,ward_type,floor_number,total_beds) "
                "VALUES(%s,%s,%s,%s) RETURNING ward_id",
                (data["ward_name"], data["ward_type"], data.get("floor_number", 1), data.get("total_beds", 0))
            )
            wid = cur.fetchone()[0]
        conn.commit()
        return jsonify({"ward_id": wid}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


# ── BEDS ───────────────────────────────────────────────────────────────────

@wards_bp.get("/<int:wid>/beds")
@jwt_required_custom
def list_beds(wid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT bed_id,ward_id,bed_number,bed_type,status FROM beds WHERE ward_id=%s ORDER BY bed_number",
            (wid,)
        )
        return jsonify(_row(cur)), 200


@wards_bp.post("/<int:wid>/beds")
@roles_required("super_admin")
def add_bed(wid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO beds(ward_id,bed_number,bed_type,status) VALUES(%s,%s,%s,'available') RETURNING bed_id",
                (wid, data["bed_number"], data.get("bed_type", "general"))
            )
            bid = cur.fetchone()[0]
            # keep total_beds in sync
            cur.execute("UPDATE wards SET total_beds = (SELECT COUNT(*) FROM beds WHERE ward_id=%s) WHERE ward_id=%s", (wid, wid))
        conn.commit()
        return jsonify({"bed_id": bid}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@wards_bp.get("/beds/available")
@jwt_required_custom
def available_beds():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT b.bed_id, b.bed_number, b.bed_type, b.status,
                      w.ward_id, w.ward_name, w.ward_type, w.floor_number
                 FROM beds b JOIN wards w ON w.ward_id = b.ward_id
                WHERE b.status = 'available' ORDER BY w.ward_name, b.bed_number"""
        )
        return jsonify(_row(cur)), 200


@wards_bp.patch("/beds/<int:bid>/status")
@roles_required("super_admin", "receptionist", "nurse")
def update_bed_status(bid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("available", "occupied", "maintenance"):
        return jsonify({"error": "Invalid status"}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE beds SET status=%s WHERE bed_id=%s", (status, bid))
        conn.commit()
        return jsonify({"message": "Bed status updated"}), 200
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


# ── SUBQUERY: Doctors with highest active patient load ─────────────────────

@wards_bp.get("/reports/busy-doctors")
@roles_required("super_admin", "doctor")
def busy_doctors():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.doctor_id, u.full_name AS doctor_name, d.specialization,
                   (SELECT COUNT(*) FROM admissions a
                     WHERE a.doctor_id = d.doctor_id AND a.status = 'active') AS active_patients
              FROM doctors d JOIN users u ON u.user_id = d.user_id
             ORDER BY active_patients DESC
            """
        )
        return jsonify(_row(cur)), 200
