import uuid
from flask import Flask, request, g


def register_middleware(app: Flask) -> None:
    @app.before_request
    def inject_correlation_id() -> None:
        # BFF is the origin — generate if missing; always propagate downstream
        g.correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

    @app.before_request
    def extract_auth() -> None:
        # JWT validation happens here. Stub: trust Authorization header as-is.
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        g.bearer_token = token

    @app.after_request
    def propagate_correlation_id(response):
        response.headers["X-Correlation-ID"] = g.get("correlation_id", "")
        return response
