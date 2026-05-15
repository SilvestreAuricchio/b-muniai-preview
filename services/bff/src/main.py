import os, yaml, logging
from flask import Flask
from flasgger import Swagger
from prometheus_flask_exporter import PrometheusMetrics
from werkzeug.middleware.proxy_fix import ProxyFix

from src.infrastructure.clients.http_backend_client import HttpBackendClient
from src.infrastructure.cache.token_cache import TokenCache
from src.infrastructure.http.middleware import register_middleware
from src.infrastructure.http.blueprints.health import health_bp
from src.infrastructure.http.blueprints.session import session_bp
from src.infrastructure.http.blueprints.users import users_bp
from src.infrastructure.http.blueprints.hospitals import hospitals_bp
from src.infrastructure.http.blueprints.slots import slots_bp
from src.infrastructure.http.blueprints.medicineres import medicineres_bp
from src.infrastructure.http.blueprints.config import config_bp
from src.infrastructure.http.blueprints.auth import auth_bp, init_oauth

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def _load_authorized_emails() -> set[str]:
    path = os.path.join(os.getenv("RESOURCES_DIR", "resources"), "authorized_psas.yaml")
    try:
        with open(path) as f:
            return set(yaml.safe_load(f)["psas"])
    except FileNotFoundError:
        logging.warning("authorized_psas.yaml not found at %s — no one can log in", path)
        return set()


def create_app() -> Flask:
    app = Flask(__name__)
    # Trust X-Forwarded-Proto and Host from nginx so request.scheme is "https" behind the proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # --- Config ---
    app.secret_key = os.getenv("BFF_SECRET_KEY", "dev-secret-change-in-production")

    itk_redis_url = os.getenv("INVITE_TOKEN_REDIS_URL")
    token_cache   = TokenCache(itk_redis_url) if itk_redis_url else None

    app.config.update(
        BFF_SECRET_KEY      = app.secret_key,
        GOOGLE_CLIENT_ID    = os.getenv("GOOGLE_CLIENT_ID", ""),
        GOOGLE_CLIENT_SECRET= os.getenv("GOOGLE_CLIENT_SECRET", ""),
        GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://localhost/bff/auth/google/callback"),
        APP_URL             = os.getenv("APP_URL", "https://localhost"),
        APP_COUNTRY         = os.getenv("APP_COUNTRY", "BR"),
        AUTHORIZED_EMAILS   = _load_authorized_emails(),
        BACKEND_CLIENT      = HttpBackendClient(os.getenv("BACKEND_URL", "http://localhost:30002")),
        TOKEN_CACHE         = token_cache,
    )

    # --- OAuth ---
    init_oauth(app)

    # --- Cross-cutting ---
    register_middleware(app)
    PrometheusMetrics(app)
    Swagger(app, template={
        "info": {"title": "MuniAI BFF API", "version": "0.1.0"},
        "securityDefinitions": {
            "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
        },
    })

    # --- Routes ---
    app.register_blueprint(health_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(hospitals_bp)
    app.register_blueprint(slots_bp)
    app.register_blueprint(medicineres_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(auth_bp)

    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", 30001))
    create_app().run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
