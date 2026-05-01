from flask import Blueprint, jsonify, g

session_bp = Blueprint("session", __name__)


@session_bp.get("/session")
def get_session():
    """
    Validate session and return user context (UC-01 Phase 1)
    ---
    tags: [auth]
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: Bearer <JWT>
    responses:
      200:
        description: Valid session
        schema:
          properties:
            sub:  {type: string, description: USER.uuid}
            role: {type: string}
            name: {type: string}
      401: {description: Missing or invalid token}
    """
    token = g.get("bearer_token", "")
    if not token:
        return jsonify(error="missing token"), 401

    # Stub: in production, validate JWT signature and decode claims
    return jsonify(sub="demo-uuid", role="SA-root", name="Demo SA")
