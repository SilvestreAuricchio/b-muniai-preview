import logging
import os
import urllib.parse
import yaml
import jwt
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, redirect, current_app
from authlib.integrations.flask_client import OAuth

auth_bp = Blueprint("auth", __name__)
oauth    = OAuth()
_log     = logging.getLogger(__name__)

_TOKEN_TTL_SECONDS = 88 * 60  # 88 minutes


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _jwt_key():
    return current_app.config["BFF_SECRET_KEY"]


def _make_token(
    userinfo: dict,
    db_uuid: str | None = None,
    role: str = "SA-root",
    itk: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub":   db_uuid or userinfo["sub"],
        "email": userinfo["email"],
        "name":  userinfo.get("name", userinfo["email"]),
        "role":  role,
        "iat":   now,
        "exp":   now + timedelta(seconds=_TOKEN_TTL_SECONDS),
    }
    if itk:
        payload["itk"] = itk
    return jwt.encode(payload, _jwt_key(), algorithm="HS256")


def _decode_token(token: str) -> dict:
    return jwt.decode(token, _jwt_key(), algorithms=["HS256"])


@auth_bp.get("/auth/google/login")
def google_login():
    """
    Redirect to Google OAuth consent screen
    ---
    tags: [auth]
    responses:
      302: {description: Redirect to Google}
      503: {description: Google OAuth not configured}
    """
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        app_url = f"{request.scheme}://{request.host}"
        return redirect(f"{app_url}/?auth_error=not_configured")
    redirect_uri = f"{request.scheme}://{request.host}/bff/auth/google/callback"
    _log.info("OAuth login  scheme=%s  host=%s  redirect_uri=%s", request.scheme, request.host, redirect_uri)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.get("/auth/google/callback")
def google_callback():
    """
    Google OAuth callback — issues session cookie and redirects to app.

    Auth resolution order:
      1. Bootstrap YAML (authorized_psas.yaml) — initial SA-root only
      2. Active user in the database — email + status=active
      3. Unauthorized
    ---
    tags: [auth]
    responses:
      302: {description: Redirect to app}
    """
    app_url = f"{request.scheme}://{request.host}"
    try:
        token    = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.userinfo()
        email    = userinfo.get("email", "")

        # 1. Bootstrap SA — static YAML allowlist
        bootstrap_emails = current_app.config["AUTHORIZED_EMAILS"]
        if email in bootstrap_emails:
            # Respect DB-level disable/deactivate even for bootstrap SAs
            backend  = current_app.config["BACKEND_CLIENT"]
            db_check, db_status = backend.get(
                f"/users/by-email?email={urllib.parse.quote(email)}&anyStatus=true", {}
            )
            if db_status == 200 and db_check.get("status") in ("disabled", "inactive"):
                _log.warning("Bootstrap SA login blocked by DB status: %s  status=%s", email, db_check["status"])
                return redirect(f"{app_url}/?auth_error=session_revoked")
            jwt_token = _make_token(userinfo, role="SA-root")
        else:
            # 2. Active database user
            backend = current_app.config["BACKEND_CLIENT"]
            db_user, status = backend.get(
                f"/users/by-email?email={urllib.parse.quote(email)}", {}
            )
            if status != 200:
                _log.warning("Login attempt for unknown/inactive email: %s", email)
                return redirect(f"{app_url}/?auth_error=unauthorized")
            jwt_token = _make_token(
                userinfo,
                db_uuid=db_user["uuid"],
                role=db_user["role"],
                itk=db_user.get("inviteToken"),
            )

        response = redirect(app_url)
        response.set_cookie(
            "muniai_token", jwt_token,
            httponly=True, secure=True, samesite="Lax",
            max_age=_TOKEN_TTL_SECONDS,
        )
        return response
    except Exception as exc:
        _log.exception("OAuth callback error: %s", exc)
        return redirect(f"{app_url}/?auth_error=oauth_failed")


@auth_bp.get("/auth/me")
def get_me():
    """
    Return current authenticated user (reads httpOnly cookie)
    ---
    tags: [auth]
    responses:
      200:
        description: Current user
        schema:
          properties:
            sub:   {type: string}
            email: {type: string}
            name:  {type: string}
            role:  {type: string}
      401: {description: Not authenticated}
    """
    token = request.cookies.get("muniai_token")
    if not token:
        return jsonify(error="not authenticated"), 401
    try:
        payload = _decode_token(token)
        return jsonify(
            sub=payload["sub"],
            email=payload["email"],
            name=payload["name"],
            role=payload["role"],
        )
    except jwt.ExpiredSignatureError:
        return jsonify(error="token expired"), 401
    except jwt.InvalidTokenError:
        return jsonify(error="invalid token"), 401


@auth_bp.get("/auth/refresh")
def refresh_token():
    """
    Re-issue JWT with a fresh 88-minute expiry (sliding session).
    Called automatically by the frontend every 44 minutes while the tab is open.
    ---
    tags: [auth]
    responses:
      200: {description: New cookie issued}
      401: {description: Not authenticated or session revoked}
    """
    token = request.cookies.get("muniai_token")
    if not token:
        return jsonify(error="not authenticated"), 401
    try:
        payload = _decode_token(token)
    except jwt.ExpiredSignatureError:
        return jsonify(error="token_expired"), 401
    except jwt.InvalidTokenError:
        return jsonify(error="invalid_token"), 401

    new_token = _make_token(
        {"sub": payload["sub"], "email": payload["email"], "name": payload["name"]},
        db_uuid=payload["sub"],
        role=payload["role"],
        itk=payload.get("itk"),
    )
    response = jsonify(ok=True)
    response.set_cookie(
        "muniai_token", new_token,
        httponly=True, secure=True, samesite="Lax",
        max_age=_TOKEN_TTL_SECONDS,
    )
    return response


@auth_bp.post("/auth/logout")
def logout():
    """
    Clear session cookie
    ---
    tags: [auth]
    responses:
      200: {description: Logged out}
    """
    response = jsonify(ok=True)
    response.delete_cookie("muniai_token", httponly=True, secure=True, samesite="Lax")
    return response
