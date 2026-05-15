import logging
from flask import Blueprint, request, jsonify, g, current_app

slots_bp = Blueprint("slots", __name__)
_log     = logging.getLogger(__name__)


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


@slots_bp.post("/slots")
def create_slot():
    """
    Create a new slot
    ---
    tags: [slots]
    parameters:
      - in: body
        required: true
        schema:
          required: [hospital_uuid, department, type, date]
          properties:
            hospital_uuid: {type: string}
            department:    {type: string, enum: [UTI, PA, PS]}
            type:          {type: string, enum: [PM, PE, CC, CM]}
            date:          {type: string, format: date}
            mediciner_crm: {type: string}
    responses:
      201: {description: Slot created}
      400: {description: Validation error}
    """
    payload = request.get_json(silent=True) or {}
    _log.info("POST /slots  corr=%s  payload=%s", g.correlation_id, payload)
    body, status = _backend().post_slot(payload, _forward_headers())
    _log.info("POST /slots  corr=%s  → status=%s", g.correlation_id, status)
    return jsonify(body), status


@slots_bp.get("/slots")
def list_slots():
    """
    List slots with optional filters and pagination
    ---
    tags: [slots]
    parameters:
      - {in: query, name: hospital_uuid, type: string}
      - {in: query, name: from_date,     type: string, format: date}
      - {in: query, name: to_date,       type: string, format: date}
      - {in: query, name: page,          type: integer}
      - {in: query, name: per_page,      type: integer}
    responses:
      200: {description: Paginated slot list}
    """
    params = {k: v for k, v in request.args.items()}
    body, status = _backend().list_slots(params, _forward_headers())
    return jsonify(body), status


@slots_bp.put("/slots/<uuid>")
def update_slot(uuid: str):
    """
    Update a slot
    ---
    tags: [slots]
    parameters:
      - {in: path, name: uuid, required: true, type: string}
      - in: body
        schema:
          properties:
            department:    {type: string, enum: [UTI, PA, PS]}
            type:          {type: string, enum: [PM, PE, CC, CM]}
            date:          {type: string, format: date}
            mediciner_crm: {type: string}
    responses:
      200: {description: Slot updated}
      400: {description: Validation error}
      404: {description: Slot not found}
    """
    payload = request.get_json(silent=True) or {}
    body, status = _backend().update_slot(uuid, payload, _forward_headers())
    return jsonify(body), status


@slots_bp.delete("/slots/<uuid>")
def delete_slot(uuid: str):
    """
    Delete a slot
    ---
    tags: [slots]
    parameters:
      - {in: path, name: uuid, required: true, type: string}
    responses:
      200: {description: Slot deleted}
      404: {description: Slot not found}
    """
    body, status = _backend().delete_slot(uuid, _forward_headers())
    return jsonify(body), status
