import os
import logging
from flask import Flask
from flasgger import Swagger
from prometheus_flask_exporter import PrometheusMetrics

from src.infrastructure.persistence.memory_user_repo import InMemoryUserRepository
from src.infrastructure.messaging.noop_log_adapter import NoOpLogAdapter
from src.infrastructure.messaging.rabbitmq_log_adapter import RabbitMQLogAdapter
from src.application.use_cases.create_user import CreateUserUseCase
from src.application.use_cases.activate_user import ActivateUserUseCase
from src.infrastructure.http.middleware import register_middleware
from src.infrastructure.http.blueprints.health import health_bp
from src.infrastructure.http.blueprints.users import users_bp

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def _build_log_adapter():
    url = os.getenv("RABBITMQ_URL")
    if url:
        return RabbitMQLogAdapter(url)
    return NoOpLogAdapter()


def create_app() -> Flask:
    app = Flask(__name__)

    # --- Infrastructure ---
    repo     = InMemoryUserRepository()
    log_port = _build_log_adapter()

    # --- Use cases ---
    app.config["USE_CASES"] = {
        "create_user":  CreateUserUseCase(repo, log_port),
        "activate_user": ActivateUserUseCase(repo, log_port),
    }

    # --- Cross-cutting ---
    register_middleware(app)
    PrometheusMetrics(app)
    Swagger(app, template={
        "info": {"title": "MuniAI Backend API", "version": "0.1.0"},
        "securityDefinitions": {
            "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
        },
    })

    # --- Routes ---
    app.register_blueprint(health_bp)
    app.register_blueprint(users_bp)

    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", 30002))
    create_app().run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
