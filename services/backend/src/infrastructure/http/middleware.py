import uuid
from flask import Flask, request, g


def register_middleware(app: Flask) -> None:
    @app.before_request
    def attach_correlation_id() -> None:
        g.correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

    @app.before_request
    def attach_auth_context() -> None:
        # In production, validate JWT here. For now, trust forwarded claims from BFF.
        g.auth_sub  = request.headers.get("X-Auth-Sub", "anonymous")
        g.auth_role = request.headers.get("X-Auth-Role", "")

    @app.after_request
    def propagate_correlation_id(response):
        response.headers["X-Correlation-ID"] = g.get("correlation_id", "")
        return response
