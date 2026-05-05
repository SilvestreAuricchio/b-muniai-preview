import uuid, jwt
from flask import Flask, request, g

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
        if token:
            try:
                from flask import current_app
                payload = jwt.decode(
                    token,
                    current_app.config["BFF_SECRET_KEY"],
                    algorithms=["HS256"],
                )
                g.auth_sub   = payload.get("sub",   "")
                g.auth_role  = payload.get("role",  "")
                g.auth_name  = payload.get("name",  "")
                g.auth_email = payload.get("email", "")
            except jwt.InvalidTokenError:
                pass

    @app.after_request
    def propagate_correlation_id(response):
        response.headers["X-Correlation-ID"] = g.get("correlation_id", "")
        return response
