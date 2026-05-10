"""
backend/app/lab/routes.py
"""
from flask import Blueprint, request, jsonify
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required

lab_bp = Blueprint("lab", __name__)

def _row(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@lab_bp.get("/orders")
@jwt_required_custom
def list_orders():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM pending_lab_orders_view")
        return jsonify(_row(cur)), 200


@lab_bp.get("/orders/all")
@jwt_required_custom
def list_all_orders():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT lo.*, p.full_name AS patient_name, u.full_name AS doctor_name
                 FROM lab_orders lo
                 JOIN admissions a ON a.admission_id = lo.admission_id
                 JOIN patients   p ON p.patient_id   = a.patient_id
                 JOIN doctors    d ON d.doctor_id     = lo.doctor_id
                 JOIN users      u ON u.user_id       = d.user_id
                ORDER BY lo.ordered_at DESC"""
        )
        return jsonify(_row(cur)), 200


@lab_bp.post("/orders")
@roles_required("super_admin", "doctor")
def create_order():
    data = request.get_json(silent=True) or {}
    required = ["admission_id", "doctor_id", "test_name"]
    if any(k not in data for k in required):
        return jsonify({"error": f"Required: {required}"}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO lab_orders(admission_id,doctor_id,test_name,priority) "
                "VALUES(%s,%s,%s,%s) RETURNING order_id",
                (data["admission_id"], data["doctor_id"], data["test_name"],
                 data.get("priority", "routine"))
            )
            oid = cur.fetchone()[0]
        conn.commit()
        return jsonify({"order_id": oid}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@lab_bp.patch("/orders/<int:oid>/status")
@roles_required("super_admin", "lab_technician")
def update_order_status(oid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("pending", "in_progress", "completed", "cancelled"):
        return jsonify({"error": "Invalid status"}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE lab_orders SET status=%s WHERE order_id=%s", (status, oid))
        conn.commit()
        return jsonify({"message": "Updated"}), 200
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@lab_bp.post("/orders/<int:oid>/result")
@roles_required("super_admin", "lab_technician")
def upload_result(oid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO lab_results(order_id,tech_id,result_summary,result_file_id,notes)
                   VALUES(%s,%s,%s,%s,%s)
                   ON CONFLICT (order_id) DO UPDATE
                   SET result_summary=EXCLUDED.result_summary,
                       result_file_id=EXCLUDED.result_file_id,
                       notes=EXCLUDED.notes,
                       resulted_at=NOW()
                   RETURNING result_id""",
                (oid, data.get("tech_id"), data.get("result_summary"),
                 data.get("result_file_id"), data.get("notes"))
            )
            rid = cur.fetchone()[0]
            cur.execute("UPDATE lab_orders SET status='completed' WHERE order_id=%s", (oid,))
        conn.commit()
        return jsonify({"result_id": rid}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@lab_bp.get("/orders/<int:oid>/result")
@jwt_required_custom
def get_result(oid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT lr.*, lo.test_name, lo.priority,
                      p.full_name AS patient_name, u.full_name AS tech_name
                 FROM lab_results lr
                 JOIN lab_orders lo ON lo.order_id = lr.order_id
                 JOIN admissions  a ON a.admission_id = lo.admission_id
                 JOIN patients    p ON p.patient_id   = a.patient_id
                 LEFT JOIN lab_technicians lt ON lt.tech_id = lr.tech_id
                 LEFT JOIN users            u ON u.user_id  = lt.user_id
                WHERE lr.order_id=%s""",
            (oid,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        cols = [d[0] for d in cur.description]
        return jsonify(dict(zip(cols, row))), 200
