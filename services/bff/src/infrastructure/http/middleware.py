import uuid, jwt, logging
from flask import Flask, request, g, jsonify, current_app, make_response

_log = logging.getLogger(__name__)

# Only skip endpoints that must work before/during the OAuth flow and health checks.
# /auth/me is intentionally NOT skipped — it must honour the email blocklist.
_ITK_SKIP_PATHS = {
    "/health",
    "/auth/google/login",
    "/auth/google/callback",
    "/auth/logout",
}


def _revoked_response():
    """Return 401 JSON and clear the session cookie in one response."""
    resp = make_response(jsonify(error="session_revoked"), 401)
    resp.delete_cookie("muniai_token", path="/", httponly=True, secure=True, samesite="Lax")
    return resp


def register_middleware(app: Flask) -> None:
    @app.before_request
    def inject_correlation_id():
        g.correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

    @app.before_request
    def extract_auth():
        token = request.cookies.get("muniai_token")
        g.auth_sub   = ""
        g.auth_role  = ""
        g.auth_name  = ""
        g.auth_email = ""
        if not token:
            return

        try:
            payload = jwt.decode(
                token,
                current_app.config["BFF_SECRET_KEY"],
                algorithms=["HS256"],
            )
        except jwt.InvalidTokenError:
            return

        g.auth_sub   = payload.get("sub",   "")
        g.auth_role  = payload.get("role",  "")
        g.auth_name  = payload.get("name",  "")
        g.auth_email = payload.get("email", "")

        if request.path not in _ITK_SKIP_PATHS:
            token_cache = current_app.config.get("TOKEN_CACHE")
            if token_cache:
                # Email blocklist — covers ALL sessions (including legacy JWTs without itk claim)
                if g.auth_email and token_cache.is_email_blocked(g.auth_email):
                    _log.warning("revoke: email_blocked  email=%s  path=%s", g.auth_email, request.path)
                    g.auth_sub   = ""
                    g.auth_role  = ""
                    g.auth_name  = ""
                    g.auth_email = ""
                    return _revoked_response()

                # itk claim check — covers new sessions only (bootstrap SA has no itk → skipped)
                itk_claim = payload.get("itk")
                if itk_claim:
                    stored = token_cache.get(g.auth_sub)
                    # None     → key not in Redis (new deployment / Redis restart) → allow
                    # "REVOKED" → explicitly revoked → block
                    # <uuid>   → mismatch = stale token (reinvited) → block
                    if stored is not None and (stored == "REVOKED" or stored != itk_claim):
                        _log.warning("revoke: itk_mismatch  sub=%s  claim=%s  stored=%s  path=%s",
                                     g.auth_sub, itk_claim, stored, request.path)
                        g.auth_sub   = ""
                        g.auth_role  = ""
                        g.auth_name  = ""
                        g.auth_email = ""
                        return _revoked_response()

    @app.after_request
    def propagate_correlation_id(response):
        response.headers["X-Correlation-ID"] = g.get("correlation_id", "")
        return response
