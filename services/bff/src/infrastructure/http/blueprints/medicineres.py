import logging
from flask import Blueprint, request, jsonify, g, current_app

medicineres_bp = Blueprint("medicineres", __name__)
_log           = logging.getLogger(__name__)


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


@medicineres_bp.get("/medicineres/crm-lookup")
def crm_lookup():
    """
    Look up a physician by CRM state and number
    ---
    tags: [medicineres]
    parameters:
      - {in: query, name: state,  required: true,  type: string}
      - {in: query, name: number, required: true,  type: string}
    responses:
      200: {description: Physician data found}
      204: {description: Not found or service unavailable}
      400: {description: Missing parameters}
    """
    state  = (request.args.get("state")  or "").strip()
    number = (request.args.get("number") or "").strip()
    body, status = _backend().lookup_crm(state, number, _forward_headers())
    if status == 204:
        return "", 204
    return jsonify(body), status


@medicineres_bp.post("/medicineres")
def create_mediciner():
    """
    Invite a new Mediciner (SA-root only)
    ---
    tags: [medicineres]
    parameters:
      - in: body
        required: true
        schema:
          required: [name, email, telephone, cpf]
          properties:
            name:         {type: string}
            email:        {type: string}
            telephone:    {type: string}
            cpf:          {type: string}
            specialty:    {type: string}
            crm_state:    {type: string}
            crm_number:   {type: string}
            hospital_uuid: {type: string}
    responses:
      201: {description: Mediciner invited}
      400: {description: Validation error}
      409: {description: Email or CPF already registered}
    """
    payload = request.get_json(silent=True) or {}
    _log.info("POST /medicineres  corr=%s  payload=%s", g.correlation_id, payload)
    body, status = _backend().create_mediciner(payload, _forward_headers())
    _log.info("POST /medicineres  corr=%s  → status=%s", g.correlation_id, status)
    return jsonify(body), status


@medicineres_bp.get("/medicineres")
def list_medicineres():
    """
    List Medicineres with pagination and optional search
    ---
    tags: [medicineres]
    parameters:
      - {in: query, name: page,     type: integer}
      - {in: query, name: per_page, type: integer}
      - {in: query, name: search,   type: string}
    responses:
      200: {description: Paginated list}
    """
    params = {k: v for k, v in request.args.items()}
    body, status = _backend().list_medicineres(params, _forward_headers())
    return jsonify(body), status


@medicineres_bp.get("/medicineres/<uuid>")
def get_mediciner(uuid: str):
    """
    Get a single Mediciner by UUID
    ---
    tags: [medicineres]
    parameters:
      - {in: path, name: uuid, required: true, type: string}
    responses:
      200: {description: Mediciner data}
      404: {description: Not found}
    """
    body, status = _backend().get_mediciner(uuid, _forward_headers())
    return jsonify(body), status


@medicineres_bp.put("/medicineres/<uuid>")
def update_mediciner(uuid: str):
    """
    Update a Mediciner profile
    ---
    tags: [medicineres]
    parameters:
      - {in: path, name: uuid, required: true, type: string}
      - in: body
        schema:
          properties:
            specialty:  {type: string}
            crm_state:  {type: string}
            crm_number: {type: string}
    responses:
      200: {description: Updated}
      404: {description: Not found}
    """
    payload = request.get_json(silent=True) or {}
    body, status = _backend().update_mediciner(uuid, payload, _forward_headers())
    return jsonify(body), status
