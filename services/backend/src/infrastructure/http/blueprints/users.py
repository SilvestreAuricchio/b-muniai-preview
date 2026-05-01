from flask import Blueprint, request, jsonify, g, current_app
from src.domain.entities.user import UserRole
from src.application.use_cases.create_user import CreateUserCommand
from src.application.use_cases.activate_user import ActivateUserCommand

users_bp = Blueprint("users", __name__)


def _uc(name: str):
    return current_app.config["USE_CASES"][name]


@users_bp.post("/users")
def create_user():
    """
    Create a new user (UC-01 Phase 2)
    ---
    tags: [users]
    parameters:
      - in: body
        required: true
        schema:
          required: [name, telephone, email, role]
          properties:
            name:      {type: string, example: "João Silva"}
            telephone: {type: string, example: "+5511999999999"}
            email:     {type: string, example: "joao@hospital.com.br"}
            role:
              type: string
              enum: [SA-root, Scheduler, Mediciner]
    responses:
      202:
        description: User created — pending OTP verification
        schema:
          properties:
            uuid:   {type: string}
            status: {type: string, example: pending}
      400: {description: Missing or invalid fields}
      409: {description: Email already registered}
    """
    body = request.get_json(silent=True) or {}
    name      = (body.get("name") or "").strip()
    telephone = (body.get("telephone") or "").strip()
    email     = (body.get("email") or "").strip()
    role_str  = (body.get("role") or "").strip()

    if not all([name, telephone, email, role_str]):
        return jsonify(error="name, telephone, email, role are required"), 400

    try:
        role = UserRole(role_str)
    except ValueError:
        return jsonify(error=f"invalid role: {role_str!r}"), 400

    try:
        user = _uc("create_user").execute(CreateUserCommand(
            name=name,
            telephone=telephone,
            email=email,
            role=role,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
        ))
    except ValueError as exc:
        return jsonify(error=str(exc)), 409

    return jsonify(uuid=user.uuid, status=user.status.value), 202


@users_bp.post("/users/<uuid>/verify")
def verify_user(uuid: str):
    """
    Verify OTP and activate user (UC-01 Phase 3)
    ---
    tags: [users]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
      - in: body
        required: true
        schema:
          required: [otp]
          properties:
            otp: {type: string, example: "123456"}
    responses:
      201: {description: User activated}
      400: {description: Missing OTP}
      404: {description: User not found}
      422: {description: Cannot activate (wrong status)}
    """
    body = request.get_json(silent=True) or {}
    otp = (body.get("otp") or "").strip()
    if not otp:
        return jsonify(error="otp is required"), 400

    # OTP validation is delegated to Challenge Service (stub: accept any 6-digit code)
    if len(otp) != 6 or not otp.isdigit():
        return jsonify(error="invalid otp format"), 400

    try:
        user = _uc("activate_user").execute(ActivateUserCommand(
            uuid=uuid,
            otp=otp,
            performed_by=uuid,        # NSA activates their own account
            correlation_id=g.correlation_id,
        ))
    except LookupError:
        return jsonify(error="user not found"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422

    return jsonify(uuid=user.uuid, status=user.status.value), 201
