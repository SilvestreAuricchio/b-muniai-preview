from flask import Blueprint, jsonify, g

session_bp = Blueprint("session", __name__)

@session_bp.get("/session")
def get_session():
    """
    Validate session and return user context (UC-01 Phase 1)
    ---
    tags: [auth]
    responses:
      200:
        description: Valid session
      401: {description: Not authenticated}
    """
    sub = g.get("auth_sub", "")
    if not sub:
        return jsonify(error="not authenticated"), 401
    return jsonify(sub=sub, role=g.auth_role, name=g.auth_name)
