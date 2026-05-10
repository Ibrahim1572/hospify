"""
backend/app/pharmacy/routes.py
"""
from flask import Blueprint, request, jsonify
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required

pharmacy_bp = Blueprint("pharmacy", __name__)

def _row(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@pharmacy_bp.get("/medicines")
@jwt_required_custom
def list_medicines():
    search = request.args.get("search", "")
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT m.*, mi.quantity_available, mi.reorder_level, mi.last_updated
                 FROM medicines m
                 LEFT JOIN medicine_inventory mi ON mi.medicine_id = m.medicine_id
                WHERE m.generic_name ILIKE %s OR m.brand_name ILIKE %s
                ORDER BY m.generic_name""",
            (f"%{search}%", f"%{search}%")
        )
        return jsonify(_row(cur)), 200


@pharmacy_bp.post("/medicines")
@roles_required("super_admin", "pharmacist")
def add_medicine():
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO medicines(generic_name,brand_name,category,unit,description) "
                "VALUES(%s,%s,%s,%s,%s) RETURNING medicine_id",
                (data["generic_name"], data.get("brand_name"), data.get("category"),
                 data.get("unit"), data.get("description"))
            )
            mid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO medicine_inventory(medicine_id,quantity_available,reorder_level) "
                "VALUES(%s,%s,%s)",
                (mid, data.get("quantity_available", 0), data.get("reorder_level", 10))
            )
        conn.commit()
        return jsonify({"medicine_id": mid}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@pharmacy_bp.get("/prescriptions/<int:admission_id>")
@jwt_required_custom
def get_prescriptions(admission_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT p.prescription_id, p.prescribed_at, p.notes,
                      u.full_name AS doctor_name,
                      json_agg(json_build_object(
                          'item_id', pi.item_id, 'medicine_id', pi.medicine_id,
                          'generic_name', m.generic_name, 'brand_name', m.brand_name,
                          'dosage', pi.dosage, 'frequency', pi.frequency,
                          'duration_days', pi.duration_days, 'instructions', pi.instructions
                      )) AS items
                 FROM prescriptions p
                 JOIN doctors d ON d.doctor_id = p.doctor_id
                 JOIN users   u ON u.user_id   = d.user_id
                 JOIN prescription_items pi ON pi.prescription_id = p.prescription_id
                 JOIN medicines m ON m.medicine_id = pi.medicine_id
                WHERE p.admission_id = %s
                GROUP BY p.prescription_id, u.full_name
                ORDER BY p.prescribed_at DESC""",
            (admission_id,)
        )
        return jsonify(_row(cur)), 200


@pharmacy_bp.post("/prescriptions")
@roles_required("super_admin", "doctor")
def create_prescription():
    data = request.get_json(silent=True) or {}
    conn = get_db()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO prescriptions(admission_id,doctor_id,notes) VALUES(%s,%s,%s) RETURNING prescription_id",
                (data["admission_id"], data["doctor_id"], data.get("notes"))
            )
            pid = cur.fetchone()[0]
            for item in data.get("items", []):
                cur.execute(
                    "INSERT INTO prescription_items(prescription_id,medicine_id,dosage,frequency,duration_days,instructions) "
                    "VALUES(%s,%s,%s,%s,%s,%s)",
                    (pid, item["medicine_id"], item.get("dosage"), item.get("frequency"),
                     item.get("duration_days"), item.get("instructions"))
                )
        conn.commit()
        return jsonify({"prescription_id": pid}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400
    finally:
        conn.autocommit = False


@pharmacy_bp.get("/inventory/low-stock")
@roles_required("super_admin", "pharmacist")
def low_stock():
    """Medicines below reorder level (subquery demo)."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT m.medicine_id, m.generic_name, m.brand_name, m.category,
                      mi.quantity_available, mi.reorder_level
                 FROM medicines m
                 JOIN medicine_inventory mi ON mi.medicine_id = m.medicine_id
                WHERE mi.quantity_available < mi.reorder_level
                ORDER BY mi.quantity_available"""
        )
        cols = [d[0] for d in cur.description]
        return jsonify([dict(zip(cols, r)) for r in cur.fetchall()]), 200


@pharmacy_bp.patch("/inventory/<int:mid>")
@roles_required("super_admin", "pharmacist")
def update_inventory(mid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE medicine_inventory SET quantity_available=%s, last_updated=NOW() WHERE medicine_id=%s",
                (data["quantity_available"], mid)
            )
        conn.commit()
        return jsonify({"message": "Inventory updated"}), 200
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400


@pharmacy_bp.get("/top-medicines")
@jwt_required_custom
def top_medicines():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM top_medicines_this_month LIMIT 20")
        cols = [d[0] for d in cur.description]
        return jsonify([dict(zip(cols, r)) for r in cur.fetchall()]), 200
