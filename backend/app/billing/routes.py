"""
backend/app/billing/routes.py — uses generate_bill stored procedure + transactions
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from ..db import get_db
from ..auth.middleware import jwt_required_custom, roles_required

billing_bp = Blueprint("billing", __name__)

def _row(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


@billing_bp.get("/")
@jwt_required_custom
def list_bills():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT b.*, p.full_name AS patient_name, u.full_name AS generated_by_name
                 FROM bills b
                 JOIN admissions a ON a.admission_id = b.admission_id
                 JOIN patients p ON p.patient_id = a.patient_id
                 LEFT JOIN users u ON u.user_id = b.generated_by
                ORDER BY b.generated_at DESC"""
        )
        return jsonify(_row(cur)), 200


@billing_bp.get("/<int:admission_id>")
@jwt_required_custom
def get_bill(admission_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT b.*, u.full_name AS generated_by_name,
                      json_agg(json_build_object(
                          'item_id', bi.bill_item_id, 'service_type', bi.service_type,
                          'description', bi.description, 'quantity', bi.quantity,
                          'unit_price', bi.unit_price, 'total_price', bi.total_price
                      )) AS items
                 FROM bills b
                 LEFT JOIN users      u  ON u.user_id = b.generated_by
                 LEFT JOIN bill_items bi ON bi.bill_id = b.bill_id
                WHERE b.admission_id = %s
                GROUP BY b.bill_id, u.full_name""",
            (admission_id,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "No bill found"}), 404
        cols = [d[0] for d in cur.description]
        return jsonify(dict(zip(cols, row))), 200


@billing_bp.post("/generate/<int:admission_id>")
@roles_required("super_admin", "billing_staff")
def generate_bill(admission_id):
    user_id = int(get_jwt_identity())
    conn = get_db()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("CALL generate_bill(%s, %s)", (admission_id, user_id))
        conn.commit()
        return jsonify({"message": "Bill generated"}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400
    finally:
        conn.autocommit = False


@billing_bp.post("/<int:bill_id>/pay")
@roles_required("super_admin", "billing_staff")
def record_payment(bill_id):
    """Transaction: record payment + update bill paid_amount + status."""
    data = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())
    amount  = data.get("amount", 0)
    method  = data.get("payment_method", "cash")

    conn = get_db()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            # Insert payment record
            cur.execute(
                "INSERT INTO payments(bill_id,amount,payment_method,received_by) VALUES(%s,%s,%s,%s)",
                (bill_id, amount, method, user_id)
            )
            # Update bill totals
            cur.execute(
                """UPDATE bills
                      SET paid_amount = paid_amount + %s,
                          status = CASE
                              WHEN paid_amount + %s >= total_amount - discount THEN 'paid'
                              WHEN paid_amount + %s > 0 THEN 'partial'
                              ELSE 'pending' END
                    WHERE bill_id = %s""",
                (amount, amount, amount, bill_id)
            )
        conn.commit()
        return jsonify({"message": "Payment recorded"}), 201
    except Exception as e:
        conn.rollback(); return jsonify({"error": str(e)}), 400
    finally:
        conn.autocommit = False


@billing_bp.get("/summary/<int:bill_id>")
@jwt_required_custom
def billing_summary(bill_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT b.bill_id, b.total_amount, b.discount, b.paid_amount, b.status,
                      b.generated_at,
                      json_agg(json_build_object(
                          'paid_at', py.paid_at, 'amount', py.amount, 'method', py.payment_method
                      )) FILTER (WHERE py.payment_id IS NOT NULL) AS payments
                 FROM bills b
                 LEFT JOIN payments py ON py.bill_id = b.bill_id
                WHERE b.bill_id = %s
                GROUP BY b.bill_id""",
            (bill_id,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        cols = [d[0] for d in cur.description]
        return jsonify(dict(zip(cols, row))), 200
