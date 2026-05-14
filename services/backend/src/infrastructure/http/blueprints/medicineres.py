import logging
import re
from flask import Blueprint, request, jsonify, g, current_app

from src.application.use_cases.create_mediciner import CreateMedicineerCommand
from src.application.use_cases.list_medicineres import ListMedicineresCommand
from src.application.use_cases.update_mediciner import UpdateMedicineerCommand

medicineres_bp = Blueprint("medicineres", __name__)
_log           = logging.getLogger(__name__)


def _uc(name: str):
    return current_app.config["USE_CASES"][name]


def _require_sa_root():
    if g.auth_role != "SA-root":
        return jsonify(error="SA-root role required"), 403
    return None


def _mediciner_dict(user, profile) -> dict:
    def _iso(dt):
        return dt.isoformat() if dt else None
    return {
        "uuid":       user.uuid,
        "name":       user.name,
        "email":      profile.email,
        "telephone":  user.telephone,
        "status":     user.status.value,
        "role":       "Mediciner",
        "cpf":        profile.cpf,
        "specialty":  profile.specialty,
        "crm_state":  profile.crm_state,
        "crm_number": profile.crm_number,
        "created_at": _iso(user.created_at),
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
    state  = (request.args.get("state")  or "").strip().upper()
    number = (request.args.get("number") or "").strip()
    if not state or not number:
        return jsonify(error="state and number are required"), 400
    result = _uc("lookup_crm").execute(state, number)
    if result is None:
        return "", 204
    return jsonify(result), 200


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
            cpf:          {type: string, example: "000.000.000-00"}
            specialty:    {type: string}
            crm_state:    {type: string}
            crm_number:   {type: string}
            hospital_uuid: {type: string}
    responses:
      201: {description: Mediciner invited}
      400: {description: Validation error}
      409: {description: Email or CPF already registered}
    """
    err = _require_sa_root()
    if err: return err

    body = request.get_json(silent=True) or {}
    _log.info("POST /medicineres  corr=%s  payload=%s", g.correlation_id, body)

    name      = (body.get("name")      or "").strip()
    email     = (body.get("email")     or "").strip()
    telephone = (body.get("telephone") or "").strip()
    cpf       = (body.get("cpf")       or "").strip()

    if not all([name, email, telephone, cpf]):
        return jsonify(error="name, email, telephone, cpf are required"), 400

    base_url = (
        request.headers.get("X-App-Base-URL")
        or f"{request.headers.get('X-Forwarded-Proto', 'https')}://{request.host}"
    )

    try:
        result = _uc("create_mediciner").execute(CreateMedicineerCommand(
            name=name,
            email=email,
            telephone=telephone,
            cpf=cpf,
            specialty=(body.get("specialty") or "").strip(),
            crm_state=(body.get("crm_state") or "").strip().upper(),
            crm_number=re.sub(r'\D', '', body.get("crm_number") or ""),
            hospital_uuid=(body.get("hospital_uuid") or "").strip(),
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
            base_url=base_url,
        ))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        _log.exception("Unexpected error creating mediciner  corr=%s", g.correlation_id)
        return jsonify(error=f"Internal server error: {type(exc).__name__}"), 500

    return jsonify(
        uuid=result.user.uuid,
        status=result.user.status.value,
        _dev={"otp": result.otp, "otpTtlSeconds": result.otp_ttl_seconds},
    ), 201


@medicineres_bp.get("/medicineres")
def list_medicineres():
    """
    List Medicineres with pagination and optional search
    ---
    tags: [medicineres]
    parameters:
      - {in: query, name: page,     type: integer, default: 1}
      - {in: query, name: per_page, type: integer, default: 20}
      - {in: query, name: search,   type: string}
    responses:
      200: {description: Paginated list}
    """
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    search   = (request.args.get("search") or "").strip() or None

    profiles, total = _uc("list_medicineres").execute(
        ListMedicineresCommand(page=page, per_page=per_page, search=search)
    )
    return jsonify({"items": profiles, "total": total, "page": page, "per_page": per_page}), 200


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
    try:
        user, profile = _uc("get_mediciner").execute(uuid)
    except LookupError:
        return jsonify(error="mediciner not found"), 404
    return jsonify(_mediciner_dict(user, profile)), 200


@medicineres_bp.put("/medicineres/<uuid>")
def update_mediciner(uuid: str):
    """
    Update a Mediciner profile (specialty / CRM)
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
      400: {description: Validation error}
    """
    body = request.get_json(silent=True) or {}
    try:
        profile = _uc("update_mediciner").execute(UpdateMedicineerCommand(
            user_uuid=uuid,
            specialty=body.get("specialty"),
            crm_state=(body.get("crm_state") or "").strip().upper() or None,
            crm_number=re.sub(r'\D', '', body.get("crm_number") or "") or None,
        ))
    except LookupError:
        return jsonify(error="mediciner not found"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify({
        "user_uuid":  profile.user_uuid,
        "specialty":  profile.specialty,
        "crm_state":  profile.crm_state,
        "crm_number": profile.crm_number,
    }), 200
