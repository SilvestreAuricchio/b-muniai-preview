import os
import logging
from flask import Flask
from flasgger import Swagger
from prometheus_flask_exporter import PrometheusMetrics

from src.infrastructure.persistence.memory_user_repo import InMemoryUserRepository
from src.infrastructure.messaging.noop_log_adapter import NoOpLogAdapter
from src.infrastructure.messaging.rabbitmq_log_adapter import RabbitMQLogAdapter
from src.infrastructure.cache.noop_otp_adapter import NoOpOTPAdapter
from src.infrastructure.cache.noop_notification_adapter import NoOpNotificationAdapter
from src.infrastructure.cache.rabbitmq_otp_publisher import RabbitMQOTPPublisher
from src.application.use_cases.create_user import CreateUserUseCase
from src.application.use_cases.verify_otp import VerifyOTPUseCase
from src.application.use_cases.approve_user import ApproveUserUseCase
from src.application.use_cases.cancel_invitation import CancelInvitationUseCase
from src.application.use_cases.list_users import ListUsersUseCase
from src.infrastructure.http.middleware import register_middleware
from src.infrastructure.http.blueprints.health import health_bp
from src.infrastructure.http.blueprints.users import users_bp

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def _build_log_adapter():
    url = os.getenv("RABBITMQ_URL")
    if url:
        return RabbitMQLogAdapter(url)
    return NoOpLogAdapter()


def _build_challenge_adapter():
    amqp_url  = os.getenv("RABBITMQ_URL")
    redis_url = os.getenv("REDIS_URL")
    if amqp_url and redis_url:
        return RabbitMQOTPPublisher(amqp_url, redis_url)
    return NoOpOTPAdapter()


def create_app() -> Flask:
    app = Flask(__name__)

    # --- Infrastructure ---
    repo         = InMemoryUserRepository()
    log_port     = _build_log_adapter()
    challenge    = _build_challenge_adapter()
    notification = NoOpNotificationAdapter()

    # --- Use cases ---
    app.config["USE_CASES"] = {
        "list_users":        ListUsersUseCase(repo),
        "create_user":       CreateUserUseCase(repo, log_port, challenge),
        "verify_otp":        VerifyOTPUseCase(repo, log_port, challenge, notification),
        "approve_user":      ApproveUserUseCase(repo, log_port, notification),
        "cancel_invitation": CancelInvitationUseCase(repo, log_port, challenge),
    }
    app.config["NOTIFICATION_PORT"] = notification

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
