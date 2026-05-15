import logging
from flask import Blueprint, request, jsonify, g, current_app
from src.domain.entities.user import UserRole, UserStatus
from src.application.use_cases.create_user import CreateUserCommand
from src.application.use_cases.verify_otp import VerifyOTPCommand
from src.application.use_cases.approve_user import ApproveUserCommand
from src.application.use_cases.cancel_invitation import CancelInvitationCommand
from src.application.use_cases.disable_user import DisableUserCommand
from src.application.use_cases.enable_user import EnableUserCommand
from src.application.use_cases.deactivate_user import DeactivateUserCommand

users_bp = Blueprint("users", __name__)
_log      = logging.getLogger(__name__)


def _uc(name: str):
    return current_app.config["USE_CASES"][name]


def _require_sa_root():
    if g.auth_role != "SA-root":
        return jsonify(error="SA-root role required"), 403
    return None


def _itk_cache():
    return current_app.config.get("INVITE_TOKEN_CACHE")


def _user_dict(u) -> dict:
    def _iso(dt):
        return dt.isoformat() if dt else None
    return {
        "uuid":            u.uuid,
        "name":            u.name,
        "email":           u.email,
        "telephone":       u.telephone,
        "role":            u.role.value,
        "status":          u.status.value,
        "createdAt":       _iso(u.created_at),
        "otpDispatchedAt": _iso(u.otp_dispatched_at),
        "otpVerifiedAt":   _iso(u.otp_verified_at),
        "activatedAt":     _iso(u.activated_at),
        "inviteToken":     u.invite_token,
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


@users_bp.get("/users/by-email")
def get_user_by_email():
    """
    Look up a user by email address — used by the BFF during OAuth login.
    Without anyStatus=true, only active users are returned.
    With anyStatus=true, all statuses are returned (used for bootstrap SA block-check).
    Internal endpoint: reachable only from the BFF on the Docker network.
    ---
    tags: [users]
    parameters:
      - in: query
        name: email
        required: true
        type: string
      - in: query
        name: anyStatus
        type: boolean
        default: false
    responses:
      200: {description: User found}
      400: {description: email param missing}
      404: {description: User not found (or not active when anyStatus omitted)}
    """
    email      = (request.args.get("email") or "").strip()
    any_status = request.args.get("anyStatus", "false").lower() == "true"
    if not email:
        return jsonify(error="email is required"), 400
    user = _uc("find_user_by_email").execute(email)
    if user is None:
        return jsonify(error="not found"), 404
    if not any_status and user.status != UserStatus.ACTIVE:
        return jsonify(error="not found"), 404
    return jsonify(_user_dict(user)), 200


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
    err = _require_sa_root()
    if err: return err

    body      = request.get_json(silent=True) or {}
    name      = (body.get("name") or "").strip()
    telephone = (body.get("telephone") or "").strip()
    email     = (body.get("email") or "").strip()
    role_str  = (body.get("role") or "").strip()

    _log.info("POST /users  corr=%s  payload=%s", g.correlation_id, body)

    if not all([name, telephone, email, role_str]):
        return jsonify(error="name, telephone, email, role are required"), 400

    try:
        role = UserRole(role_str)
    except ValueError:
        return jsonify(error=f"invalid role: {role_str!r}"), 400

    base_url = (
        request.headers.get("X-App-Base-URL")
        or f"{request.headers.get('X-Forwarded-Proto', 'https')}://{request.host}"
    )

    hospital_uuid = (body.get("hospitalUuid") or "").strip()

    try:
        result = _uc("create_user").execute(CreateUserCommand(
            name=name, telephone=telephone, email=email, role=role,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
            base_url=base_url,
            hospital_uuid=hospital_uuid,
        ))
    except ValueError as exc:
        return jsonify(error=str(exc)), 409
    except Exception as exc:
        _log.exception("Unexpected error creating user  corr=%s", g.correlation_id)
        return jsonify(error=f"Internal server error: {type(exc).__name__}"), 500

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
    except Exception as exc:
        _log.exception("Unexpected error verifying OTP uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error=f"Internal server error: {type(exc).__name__}"), 500

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
      403: {description: SA-root role required}
      404: {description: User not found}
      422: {description: User has not verified OTP yet}
    """
    err = _require_sa_root()
    if err: return err
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
    except Exception as exc:
        _log.exception("Unexpected error approving user uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error=f"Internal server error: {type(exc).__name__}"), 500

    cache = _itk_cache()
    if cache and user.invite_token:
        cache.activate(user.uuid, user.email, user.invite_token)

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
      403: {description: SA-root role required}
      404: {description: User not found}
      422: {description: User is not cancellable}
    """
    err = _require_sa_root()
    if err: return err
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
    except Exception as exc:
        _log.exception("Unexpected error cancelling invitation uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error=f"Internal server error: {type(exc).__name__}"), 500

    return jsonify(_user_dict(user)), 200


@users_bp.post("/users/<uuid>/disable")
def disable_user(uuid: str):
    """
    Disable an active user — temporary suspension (SA-root only)
    ---
    tags: [users]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
    responses:
      200: {description: User disabled}
      403: {description: SA-root role required}
      404: {description: User not found}
      422: {description: User is not active}
    """
    err = _require_sa_root()
    if err: return err
    try:
        user = _uc("disable_user").execute(DisableUserCommand(
            uuid=uuid,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
        ))
    except LookupError:
        return jsonify(error="user not found"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422
    except Exception:
        _log.exception("Unexpected error disabling user uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error="Internal server error"), 500

    cache = _itk_cache()
    if cache:
        cache.revoke(user.uuid, user.email)

    return jsonify(_user_dict(user)), 200


@users_bp.post("/users/<uuid>/enable")
def enable_user(uuid: str):
    """
    Re-enable a disabled user (SA-root only)
    ---
    tags: [users]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
    responses:
      200: {description: User re-enabled}
      403: {description: SA-root role required}
      404: {description: User not found}
      422: {description: User is not disabled}
    """
    err = _require_sa_root()
    if err: return err
    try:
        user = _uc("enable_user").execute(EnableUserCommand(
            uuid=uuid,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
        ))
    except LookupError:
        return jsonify(error="user not found"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422
    except Exception:
        _log.exception("Unexpected error enabling user uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error="Internal server error"), 500

    cache = _itk_cache()
    if cache:
        cache.unblock(user.uuid, user.email)
        if user.invite_token:
            cache.set(user.uuid, user.invite_token)

    return jsonify(_user_dict(user)), 200


@users_bp.post("/users/<uuid>/deactivate")
def deactivate_user(uuid: str):
    """
    Permanently deactivate an active or disabled user (SA-root only)
    ---
    tags: [users]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
    responses:
      200: {description: User deactivated}
      403: {description: SA-root role required}
      404: {description: User not found}
      422: {description: User cannot be deactivated from current status}
    """
    err = _require_sa_root()
    if err: return err
    try:
        user = _uc("deactivate_user").execute(DeactivateUserCommand(
            uuid=uuid,
            performed_by=g.auth_sub,
            correlation_id=g.correlation_id,
        ))
    except LookupError:
        return jsonify(error="user not found"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422
    except Exception:
        _log.exception("Unexpected error deactivating user uuid=%s  corr=%s", uuid, g.correlation_id)
        return jsonify(error="Internal server error"), 500

    cache = _itk_cache()
    if cache:
        cache.revoke(user.uuid, user.email)

    return jsonify(_user_dict(user)), 200


@users_bp.get("/users/<uuid>/history")
def get_invite_history(uuid: str):
    """
    Return previous invitation cycles for a user (oldest first).
    Each record is a snapshot saved before a reinvite reset the lifecycle timestamps.
    ---
    tags: [users]
    parameters:
      - in: path
        name: uuid
        required: true
        type: string
    responses:
      200: {description: List of past invite cycles}
      404: {description: User not found}
    """
    def _iso(dt):
        return dt.isoformat() if dt else None

    try:
        result = _uc("list_invite_history").execute(uuid)
    except LookupError:
        return jsonify(error="user not found"), 404

    return jsonify([{
        "invitedAt":       _iso(r.invited_at),
        "otpDispatchedAt": _iso(r.otp_dispatched_at),
        "otpVerifiedAt":   _iso(r.otp_verified_at),
        "activatedAt":     _iso(r.activated_at),
    } for r in result.records]), 200


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
