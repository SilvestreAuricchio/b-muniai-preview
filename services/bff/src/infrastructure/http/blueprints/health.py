from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    """
    Health check
    ---
    tags: [ops]
    responses:
      200:
        description: BFF is healthy
        schema:
          properties:
            status:  {type: string, example: ok}
            service: {type: string, example: bff}
    """
    return jsonify(status="ok", service="bff")
