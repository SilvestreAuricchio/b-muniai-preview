import logging
import math
from datetime import date, datetime

from flask import Blueprint, request, jsonify, g, current_app
from src.application.use_cases.update_slot import UNSET

slots_bp = Blueprint("slots", __name__)
_log     = logging.getLogger(__name__)


def _uc(name: str):
    uc = current_app.config["USE_CASES"].get(name)
    if uc is None:
        from flask import abort
        abort(503, description="Slot persistence not configured")
    return uc


def _slot_dict(s) -> dict:
    return {
        "uuid":          s.uuid,
        "hospital_uuid": s.hospital_uuid,
        "department":    s.department,
        "type":          s.type,
        "date":          s.date.isoformat() if isinstance(s.date, date) else s.date,
        "mediciner_crm": s.mediciner_crm,
        "created_by":    s.created_by,
        "created_at":    (
            s.created_at.isoformat()
            if isinstance(s.created_at, datetime)
            else s.created_at
        ),
    }


def _parse_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field} must be a valid ISO date (YYYY-MM-DD)")


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
    body          = request.get_json(silent=True) or {}
    hospital_uuid = (body.get("hospital_uuid") or "").strip()
    department    = (body.get("department") or "").strip()
    slot_type     = (body.get("type") or "").strip()
    raw_date      = (body.get("date") or "").strip()
    mediciner_crm = (body.get("mediciner_crm") or "").strip() or None

    _log.info("POST /slots  corr=%s  payload=%s", g.correlation_id, body)

    if not all([hospital_uuid, department, slot_type, raw_date]):
        return jsonify(error="hospital_uuid, department, type, date are required"), 400

    try:
        slot_date = date.fromisoformat(raw_date)
    except ValueError:
        return jsonify(error="date must be a valid ISO date (YYYY-MM-DD)"), 400

    try:
        slot = _uc("create_slot").execute(
            hospital_uuid=hospital_uuid,
            department=department,
            slot_type=slot_type,
            slot_date=slot_date,
            created_by=g.auth_sub,
            mediciner_crm=mediciner_crm,
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:
        _log.exception("Unexpected error creating slot  corr=%s", g.correlation_id)
        return jsonify(error="Internal server error"), 500

    return jsonify(_slot_dict(slot)), 201


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
      - {in: query, name: page,          type: integer, default: 1}
      - {in: query, name: per_page,      type: integer, default: 20}
    responses:
      200: {description: Paginated slot list}
      400: {description: Invalid date format}
    """
    try:
        hospital_uuid = request.args.get("hospital_uuid") or None
        from_date     = _parse_date(request.args.get("from_date"), "from_date")
        to_date       = _parse_date(request.args.get("to_date"),   "to_date")
        page          = max(1, int(request.args.get("page",     1)))
        per_page      = max(1, int(request.args.get("per_page", 20)))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    items, total = _uc("list_slots").execute(
        hospital_uuid=hospital_uuid,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page,
    )
    pages = math.ceil(total / per_page) if per_page else 1
    return jsonify({
        "items":    [_slot_dict(s) for s in items],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    pages,
    }), 200


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
    body     = request.get_json(silent=True) or {}
    crm_arg  = UNSET

    department = body.get("department")
    slot_type  = body.get("type")
    raw_date   = body.get("date")

    if "mediciner_crm" in body:
        crm_val = body["mediciner_crm"]
        crm_arg = (crm_val or "").strip() or None

    slot_date = None
    if raw_date is not None:
        try:
            slot_date = date.fromisoformat(raw_date)
        except ValueError:
            return jsonify(error="date must be a valid ISO date (YYYY-MM-DD)"), 400

    try:
        slot = _uc("update_slot").execute(
            uuid=uuid,
            department=department or None,
            slot_type=slot_type or None,
            slot_date=slot_date,
            mediciner_crm=crm_arg,
        )
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:
        _log.exception("Unexpected error updating slot uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error="Internal server error"), 500

    return jsonify(_slot_dict(slot)), 200


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
    try:
        _uc("delete_slot").execute(uuid)
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except Exception:
        _log.exception("Unexpected error deleting slot uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error="Internal server error"), 500

    return jsonify({"deleted": True}), 200
