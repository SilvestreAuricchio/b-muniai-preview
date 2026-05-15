import logging
from flask import Blueprint, request, jsonify, g, current_app

hospitals_bp = Blueprint("hospitals", __name__)
_log         = logging.getLogger(__name__)


def _backend():
    return current_app.config["BACKEND_CLIENT"]


def _forward_headers() -> dict:
    return {
        "X-Correlation-ID": g.correlation_id,
        "X-Auth-Sub":       g.get("auth_sub",  ""),
        "X-Auth-Role":      g.get("auth_role", ""),
        "X-App-Base-URL":   f"{request.scheme}://{request.host}",
        "Content-Type":     "application/json",
    }


@hospitals_bp.get("/hospitals")
def list_hospitals():
    """
    List all hospitals
    ---
    tags: [hospitals]
    responses:
      200: {description: List of hospitals}
    """
    body, status = _backend().get("/hospitals", _forward_headers())
    return jsonify(body), status


@hospitals_bp.post("/hospitals")
def create_hospital():
    """
    Create a new hospital (SA-root only)
    ---
    tags: [hospitals]
    parameters:
      - in: body
        required: true
        schema:
          required: [cnpj, name, address, slotTypes]
          properties:
            cnpj:      {type: string}
            name:      {type: string}
            address:   {type: string}
            slotTypes: {type: array, items: {type: string}}
    responses:
      201: {description: Hospital created}
      400: {description: Validation error}
      409: {description: CNPJ already registered}
    """
    payload = request.get_json(silent=True) or {}
    _log.info("POST /hospitals  corr=%s  payload=%s", g.correlation_id, payload)
    body, status = _backend().post("/hospitals", payload, _forward_headers())
    _log.info("POST /hospitals  corr=%s  → status=%s", g.correlation_id, status)
    return jsonify(body), status


@hospitals_bp.get("/hospitals/<uuid>")
def get_hospital(uuid: str):
    """
    Get a single hospital by UUID
    ---
    tags: [hospitals]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
    responses:
      200: {description: Hospital found}
      404: {description: Hospital not found}
    """
    body, status = _backend().get(f"/hospitals/{uuid}", _forward_headers())
    return jsonify(body), status


@hospitals_bp.put("/hospitals/<uuid>")
def update_hospital(uuid: str):
    """
    Update hospital profile (SA-root only)
    ---
    tags: [hospitals]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
      - in: body
        required: true
        schema:
          required: [name, address, slotTypes]
          properties:
            name:      {type: string}
            address:   {type: string}
            slotTypes: {type: array, items: {type: string}}
    responses:
      200: {description: Hospital updated}
      400: {description: Missing fields}
      404: {description: Hospital not found}
    """
    payload = request.get_json(silent=True) or {}
    body, status = _backend().put(f"/hospitals/{uuid}", payload, _forward_headers())
    return jsonify(body), status
