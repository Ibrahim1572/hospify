"""
backend/app/auth/routes.py — /login, /logout, /refresh, /me
"""
from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies
)
from werkzeug.security import check_password_hash, generate_password_hash
from ..db import get_db

auth_bp = Blueprint("auth", __name__)


def _user_by_email(email: str):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT user_id, full_name, email, password_hash, role, is_active "
            "FROM users WHERE email = %s",
            (email,)
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "user_id": row[0], "full_name": row[1], "email": row[2],
        "password_hash": row[3], "role": row[4], "is_active": row[5]
    }


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = _user_by_email(email)
    if not user or not user["is_active"]:
        return jsonify({"error": "Invalid credentials"}), 401
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    additional_claims = {"role": user["role"], "full_name": user["full_name"]}
    access_token  = create_access_token(identity=str(user["user_id"]), additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=str(user["user_id"]))

    resp = make_response(jsonify({
        "user_id":   user["user_id"],
        "full_name": user["full_name"],
        "email":     user["email"],
        "role":      user["role"],
    }), 200)
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


@auth_bp.post("/logout")
def logout():
    resp = make_response(jsonify({"message": "Logged out"}), 200)
    unset_jwt_cookies(resp)
    return resp


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    # Re-load role from DB so revoked/deactivated users can't refresh
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT role, full_name, is_active FROM users WHERE user_id = %s", (identity,))
        row = cur.fetchone()
    if not row or not row[2]:
        return jsonify({"error": "Account inactive"}), 401

    access_token = create_access_token(
        identity=identity,
        additional_claims={"role": row[0], "full_name": row[1]}
    )
    resp = make_response(jsonify({"message": "Token refreshed"}), 200)
    set_access_cookies(resp, access_token)
    return resp


@auth_bp.get("/me")
@jwt_required()
def me():
    claims = get_jwt()
    return jsonify({
        "user_id":   get_jwt_identity(),
        "full_name": claims.get("full_name"),
        "role":      claims.get("role"),
    }), 200
