from flask import Blueprint, request, jsonify, g, current_app
from src.domain.entities.user import UserRole
from src.application.use_cases.create_user import CreateUserCommand
from src.application.use_cases.verify_otp import VerifyOTPCommand
from src.application.use_cases.approve_user import ApproveUserCommand
from src.application.use_cases.cancel_invitation import CancelInvitationCommand

users_bp = Blueprint("users", __name__)


def _uc(name: str):
    return current_app.config["USE_CASES"][name]


def _user_dict(u) -> dict:
    return {
        "uuid":            u.uuid,
        "name":            u.name,
        "email":           u.email,
        "telephone":       u.telephone,
        "role":            u.role.value,
        "status":          u.status.value,
        "otpDispatchedAt": u.otp_dispatched_at.isoformat() if u.otp_dispatched_at else None,
    }


@users_bp.get("/users")
def list_users():
    """
    List all users
    ---
    tags: [users]
    responses:
      200:
        description: List of users
    """
    users = _uc("list_users").execute()
    return jsonify([_user_dict(u) for u in users])


@users_bp.post("/users")
def create_user():
    """
    Invite a new user and issue OTP to the invitee (UC-01 Phase 2)
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
            role:      {type: string, enum: [SA-root, Scheduler, Mediciner]}
    responses:
      202:
        description: Invitation sent — OTP delivered to invitee
      400: {description: Missing or invalid fields}
      409: {description: Email already registered}
    """
    body      = request.get_json(silent=True) or {}
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
        result = _uc("create_user").execute(CreateUserCommand(
            name=name, telephone=telephone, email=email, role=role,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
        ))
    except ValueError as exc:
        return jsonify(error=str(exc)), 409

    return jsonify(
        uuid=result.user.uuid,
        status=result.user.status.value,
        # DEV only — channel=None means OTP is logged, not delivered. Remove in production.
        _dev={"otp": result.otp, "otpTtlSeconds": result.otp_ttl_seconds},
    ), 202


@users_bp.post("/users/<uuid>/verify")
def verify_user(uuid: str):
    """
    Invitee submits OTP — transitions to pending_approval and notifies PSA (UC-01 Phase 3a)
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
      200: {description: OTP verified — awaiting PSA approval}
      400: {description: Missing or invalid OTP}
      404: {description: User not found}
      422: {description: Wrong status or invalid OTP}
    """
    body = request.get_json(silent=True) or {}
    otp  = (body.get("otp") or "").strip()
    if not otp:
        return jsonify(error="otp is required"), 400

    try:
        user = _uc("verify_otp").execute(VerifyOTPCommand(
            uuid=uuid, otp=otp, correlation_id=g.correlation_id,
        ))
    except LookupError:
        return jsonify(error="user not found"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422

    return jsonify(_user_dict(user)), 200


@users_bp.post("/users/<uuid>/approve")
def approve_user(uuid: str):
    """
    PSA approves the invitee — activates the user (UC-01 Phase 3b)
    ---
    tags: [users]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
    responses:
      201: {description: User activated}
      404: {description: User not found}
      422: {description: User has not verified OTP yet}
    """
    try:
        user = _uc("approve_user").execute(ApproveUserCommand(
            uuid=uuid,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
        ))
    except LookupError:
        return jsonify(error="user not found"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422

    return jsonify(_user_dict(user)), 201


@users_bp.delete("/users/<uuid>/invitation")
def cancel_invitation(uuid: str):
    """
    Cancel a pending or pending_approval invitation (PSA only)
    ---
    tags: [users]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
    responses:
      200: {description: Invitation cancelled}
      404: {description: User not found}
      422: {description: User is not cancellable}
    """
    try:
        user = _uc("cancel_invitation").execute(CancelInvitationCommand(
            uuid=uuid,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
        ))
    except LookupError:
        return jsonify(error="user not found"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422

    return jsonify(_user_dict(user)), 200


@users_bp.get("/notifications")
def get_notifications():
    """
    Poll PSA notifications (USER_OTP_VERIFIED requires approval, USER_ACTIVATED for audit)
    ---
    tags: [users]
    responses:
      200:
        description: List of pending notifications (consumed on read)
    """
    notification_port = current_app.config["NOTIFICATION_PORT"]
    events = notification_port.pop_for_psa(g.auth_sub)
    return jsonify(events), 200
