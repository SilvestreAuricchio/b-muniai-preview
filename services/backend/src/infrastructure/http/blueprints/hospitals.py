import logging
from flask import Blueprint, request, jsonify, g, current_app
from src.application.use_cases.create_hospital import CreateHospitalCommand
from src.application.use_cases.update_hospital import UpdateHospitalCommand

hospitals_bp = Blueprint("hospitals", __name__)
_log         = logging.getLogger(__name__)


def _uc(name: str):
    return current_app.config["USE_CASES"][name]


def _hospital_dict(h, scheduler_count: int = 0) -> dict:
    return {
        "uuid":           h.uuid,
        "cnpj":           h.cnpj,
        "name":           h.name,
        "address":        h.address,
        "slotTypes":      [s.value for s in h.slot_types],
        "schedulerCount": scheduler_count,
    }


@hospitals_bp.get("/hospitals")
def list_hospitals():
    """
    List hospitals (all for SA-root, scoped for Scheduler)
    ---
    tags: [hospitals]
    responses:
      200:
        description: List of hospitals with scheduler counts
    """
    user_uuid = g.auth_sub if g.auth_role == "Scheduler" else None
    result    = _uc("list_hospitals").execute(user_uuid=user_uuid)
    return jsonify([
        _hospital_dict(h, result.scheduler_counts.get(h.uuid, 0))
        for h in result.hospitals
    ]), 200


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
            cnpj:      {type: string, example: "33.EMA.SAM/E007-81"}
            name:      {type: string, example: "Hospital Central"}
            address:   {type: string, example: "Rua das Flores, 100, São Paulo"}
            slotTypes: {type: array, items: {type: string, enum: [UTI, PS, PA, CC, ENF]}}
    responses:
      201: {description: Hospital created}
      400: {description: Missing or invalid fields}
      409: {description: CNPJ already registered}
    """
    body       = request.get_json(silent=True) or {}
    cnpj       = (body.get("cnpj") or "").strip()
    name       = (body.get("name") or "").strip()
    address    = (body.get("address") or "").strip()
    slot_types = body.get("slotTypes") or []

    _log.info("POST /hospitals  corr=%s  payload=%s", g.correlation_id, body)

    if not all([cnpj, name, address]):
        return jsonify(error="cnpj, name, address are required"), 400
    if not isinstance(slot_types, list):
        return jsonify(error="slotTypes must be an array"), 400

    try:
        result = _uc("create_hospital").execute(CreateHospitalCommand(
            cnpj=cnpj, name=name, address=address, slot_types=slot_types,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
            country=current_app.config.get("APP_COUNTRY", "BR"),
        ))
    except ValueError as exc:
        return jsonify(error=str(exc)), 409
    except Exception:
        _log.exception("Unexpected error creating hospital  corr=%s", g.correlation_id)
        return jsonify(error="Internal server error"), 500

    return jsonify(_hospital_dict(result.hospital)), 201


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
    try:
        hospital = _uc("get_hospital").execute(uuid)
    except LookupError:
        return jsonify(error="hospital not found"), 404

    result = _uc("list_hospitals").execute()
    count  = result.scheduler_counts.get(hospital.uuid, 0)
    return jsonify(_hospital_dict(hospital, count)), 200


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
            slotTypes: {type: array, items: {type: string, enum: [UTI, PS, PA, CC, ENF]}}
    responses:
      200: {description: Hospital updated}
      400: {description: Missing fields}
      404: {description: Hospital not found}
    """
    body       = request.get_json(silent=True) or {}
    name       = (body.get("name") or "").strip()
    address    = (body.get("address") or "").strip()
    slot_types = body.get("slotTypes") or []

    if not all([name, address]):
        return jsonify(error="name, address are required"), 400

    try:
        hospital = _uc("update_hospital").execute(UpdateHospitalCommand(
            uuid=uuid,
            name=name,
            address=address,
            slot_types=slot_types,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
        ))
    except LookupError:
        return jsonify(error="hospital not found"), 404
    except Exception:
        _log.exception("Unexpected error updating hospital uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error="Internal server error"), 500

    return jsonify(_hospital_dict(hospital)), 200
