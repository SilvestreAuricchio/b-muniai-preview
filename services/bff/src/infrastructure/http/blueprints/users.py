from flask import Blueprint, request, jsonify, g, current_app

users_bp = Blueprint("users", __name__)


def _backend():
    return current_app.config["BACKEND_CLIENT"]


def _forward_headers() -> dict:
    return {
        "X-Correlation-ID": g.correlation_id,
        "X-Auth-Sub": "demo-uuid",    # decoded from JWT in production
        "X-Auth-Role": "SA-root",
        "Content-Type": "application/json",
    }


@users_bp.post("/users")
def create_user():
    """
    Forward create-user request to Backend (UC-01 Phase 2)
    ---
    tags: [users]
    parameters:
      - in: body
        required: true
        schema:
          required: [name, telephone, email, role]
          properties:
            name:      {type: string}
            telephone: {type: string}
            email:     {type: string}
            role:      {type: string, enum: [SA-root, Scheduler, Mediciner]}
    responses:
      202: {description: Invitation sent}
      400: {description: Validation error}
      409: {description: Email already registered}
    """
    body, status = _backend().post("/users", request.get_json(silent=True) or {}, _forward_headers())
    return jsonify(body), status


@users_bp.post("/users/<uuid>/verify")
def verify_user(uuid: str):
    """
    Forward OTP verification to Backend (UC-01 Phase 3)
    ---
    tags: [users]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
      - in: body
        required: true
        schema:
          required: [otp]
          properties:
            otp: {type: string}
    responses:
      201: {description: User activated}
      404: {description: User not found}
    """
    body, status = _backend().post(f"/users/{uuid}/verify", request.get_json(silent=True) or {}, _forward_headers())
    return jsonify(body), status
