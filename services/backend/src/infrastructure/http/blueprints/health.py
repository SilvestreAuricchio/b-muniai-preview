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
        description: Service is healthy
        schema:
          properties:
            status: {type: string, example: ok}
            service: {type: string, example: backend}
    """
    return jsonify(status="ok", service="backend")
