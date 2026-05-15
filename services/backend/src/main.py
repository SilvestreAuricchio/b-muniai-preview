import os
import logging
from flask import Flask
from flasgger import Swagger
from prometheus_flask_exporter import PrometheusMetrics

from src.infrastructure.persistence.memory_user_repo import InMemoryUserRepository
from src.infrastructure.persistence.in_memory_hospital_repository import InMemoryHospitalRepository
from src.infrastructure.messaging.noop_log_adapter import NoOpLogAdapter
from src.infrastructure.messaging.rabbitmq_log_adapter import RabbitMQLogAdapter
from src.infrastructure.messaging.noop_audit_publisher import NoOpAuditPublisher
from src.infrastructure.messaging.hospital_audit_publisher import HospitalAuditPublisher
from src.infrastructure.cache.noop_otp_adapter import NoOpOTPAdapter
from src.infrastructure.cache.noop_notification_adapter import NoOpNotificationAdapter
from src.infrastructure.cache.invite_token_cache import InviteTokenCache
from src.infrastructure.messaging.smtp_notification_adapter import SmtpNotificationAdapter
from src.infrastructure.cache.rabbitmq_otp_publisher import RabbitMQOTPPublisher
from src.application.use_cases.create_user import CreateUserUseCase
from src.application.use_cases.verify_otp import VerifyOTPUseCase
from src.application.use_cases.approve_user import ApproveUserUseCase
from src.application.use_cases.cancel_invitation import CancelInvitationUseCase
from src.application.use_cases.list_users import ListUsersUseCase
from src.application.use_cases.find_user_by_email import FindUserByEmailUseCase
from src.application.use_cases.create_hospital import CreateHospitalUseCase
from src.application.use_cases.list_hospitals import ListHospitalsUseCase
from src.application.use_cases.get_hospital import GetHospitalUseCase
from src.application.use_cases.update_hospital import UpdateHospitalUseCase
from src.application.use_cases.disable_user import DisableUserUseCase
from src.application.use_cases.enable_user import EnableUserUseCase
from src.application.use_cases.deactivate_user import DeactivateUserUseCase
from src.application.use_cases.list_invite_history import ListInviteHistoryUseCase
from src.application.use_cases.create_slot import CreateSlotUseCase
from src.application.use_cases.list_slots import ListSlotsUseCase
from src.application.use_cases.update_slot import UpdateSlotUseCase
from src.application.use_cases.delete_slot import DeleteSlotUseCase
from src.application.use_cases.create_mediciner import CreateMedicineerUseCase
from src.application.use_cases.list_medicineres import ListMedicineresUseCase
from src.application.use_cases.get_mediciner import GetMedicineerUseCase
from src.application.use_cases.update_mediciner import UpdateMedicineerUseCase
from src.application.use_cases.lookup_crm import LookupCrmUseCase
from src.infrastructure.external.crm_lookup_adapter import CrmLookupAdapter
from src.infrastructure.http.middleware import register_middleware
from src.infrastructure.http.blueprints.health import health_bp
from src.infrastructure.http.blueprints.users import users_bp
from src.infrastructure.http.blueprints.hospitals import hospitals_bp
from src.infrastructure.http.blueprints.slots import slots_bp
from src.infrastructure.http.blueprints.medicineres import medicineres_bp

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


def _build_audit_publisher():
    url = os.getenv("RABBITMQ_URL")
    if url:
        return HospitalAuditPublisher(url)
    return NoOpAuditPublisher()


def _build_notification_adapter():
    host = os.getenv("SMTP_HOST", "")
    if not host:
        return NoOpNotificationAdapter()
    return SmtpNotificationAdapter(
        host=host,
        port=int(os.getenv("SMTP_PORT", "587")),
        user=os.getenv("SMTP_USER", ""),
        password=os.getenv("SMTP_PASSWORD", ""),
        from_addr=os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")),
    )


def _build_repos():
    postgres_url = os.getenv("POSTGRES_URL")
    if postgres_url:
        from sqlalchemy import create_engine
        from src.infrastructure.persistence.schema import create_schema
        from src.infrastructure.persistence.postgres_user_repository import PostgresUserRepository
        from src.infrastructure.persistence.postgres_hospital_repository import PostgresHospitalRepository
        from src.infrastructure.persistence.postgres_slot_repository import PostgresSlotRepository
        from src.infrastructure.persistence.postgres_mediciner_repository import PostgresMedicineerRepository
        engine = create_engine(postgres_url)
        create_schema(engine)
        slot_repo      = PostgresSlotRepository(engine)
        mediciner_repo = PostgresMedicineerRepository(engine)
        return PostgresUserRepository(engine), PostgresHospitalRepository(engine), slot_repo, mediciner_repo
    return InMemoryUserRepository(), InMemoryHospitalRepository(), None, None


def _build_invite_token_cache():
    redis_url = os.getenv("INVITE_TOKEN_REDIS_URL")
    if redis_url:
        return InviteTokenCache(redis_url)
    return None


def _sync_revoked_users(repo, cache) -> None:
    """Sync Redis block state with DB on startup — blocks inactive/disabled, unblocks active."""
    if cache is None:
        return
    from src.domain.entities.user import UserStatus
    for user in repo.list_all():
        if user.status in (UserStatus.INACTIVE, UserStatus.DISABLED):
            cache.revoke(user.uuid, user.email)
        elif user.status == UserStatus.ACTIVE and user.invite_token:
            cache.activate(user.uuid, user.email, user.invite_token)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["APP_COUNTRY"] = os.getenv("APP_COUNTRY", "BR")

    # --- Infrastructure ---
    repo, hospital_repo, slot_repo, mediciner_repo = _build_repos()
    log_port        = _build_log_adapter()
    challenge       = _build_challenge_adapter()
    notification    = _build_notification_adapter()
    audit_publisher = _build_audit_publisher()
    itk_cache       = _build_invite_token_cache()
    crm_adapter     = CrmLookupAdapter()
    _sync_revoked_users(repo, itk_cache)

    # --- Use cases ---
    app.config["USE_CASES"] = {
        "list_users":          ListUsersUseCase(repo),
        "find_user_by_email":  FindUserByEmailUseCase(repo),
        "create_user":         CreateUserUseCase(repo, log_port, challenge, hospital_repo),
        "verify_otp":          VerifyOTPUseCase(repo, log_port, challenge, notification),
        "approve_user":        ApproveUserUseCase(repo, log_port, notification),
        "cancel_invitation":   CancelInvitationUseCase(repo, log_port, challenge),
        "create_hospital":     CreateHospitalUseCase(hospital_repo, log_port, audit_publisher),
        "list_hospitals":      ListHospitalsUseCase(hospital_repo),
        "get_hospital":        GetHospitalUseCase(hospital_repo),
        "update_hospital":     UpdateHospitalUseCase(hospital_repo, log_port, audit_publisher),
        "disable_user":        DisableUserUseCase(repo, log_port),
        "enable_user":         EnableUserUseCase(repo, log_port),
        "deactivate_user":     DeactivateUserUseCase(repo, log_port),
        "list_invite_history": ListInviteHistoryUseCase(repo),
        "create_slot":         CreateSlotUseCase(slot_repo) if slot_repo else None,
        "list_slots":          ListSlotsUseCase(slot_repo)  if slot_repo else None,
        "update_slot":         UpdateSlotUseCase(slot_repo) if slot_repo else None,
        "delete_slot":         DeleteSlotUseCase(slot_repo) if slot_repo else None,
        "create_mediciner":    CreateMedicineerUseCase(
            create_user_uc=CreateUserUseCase(repo, log_port, challenge, hospital_repo),
            mediciner_repo=mediciner_repo,
            hospital_repo=hospital_repo,
            log=log_port,
        ) if mediciner_repo else None,
        "list_medicineres":    ListMedicineresUseCase(mediciner_repo) if mediciner_repo else None,
        "get_mediciner":       GetMedicineerUseCase(repo, mediciner_repo) if mediciner_repo else None,
        "update_mediciner":    UpdateMedicineerUseCase(mediciner_repo) if mediciner_repo else None,
        "lookup_crm":          LookupCrmUseCase(crm_adapter),
    }
    app.config["NOTIFICATION_PORT"]  = notification
    app.config["INVITE_TOKEN_CACHE"] = itk_cache

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
    app.register_blueprint(hospitals_bp)
    app.register_blueprint(slots_bp)
    app.register_blueprint(medicineres_bp)

    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", 30002))
    create_app().run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
