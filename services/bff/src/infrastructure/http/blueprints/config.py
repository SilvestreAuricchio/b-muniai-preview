import logging
from flask import Blueprint, jsonify, g, current_app

config_bp = Blueprint("config", __name__)
_log       = logging.getLogger(__name__)


@config_bp.get("/config")
def get_config():
    """
    Return app-level configuration visible to the authenticated frontend.
    ---
    tags: [config]
    responses:
      200:
        description: App configuration
        schema:
          properties:
            country: {type: string, example: "BR", description: "ISO-3166-1 alpha-2 country code driving tax ID format and validation"}
      401: {description: Not authenticated}
    """
    if not g.auth_sub:
        return jsonify(error="not authenticated"), 401
    return jsonify(country=current_app.config.get("APP_COUNTRY", "BR")), 200
