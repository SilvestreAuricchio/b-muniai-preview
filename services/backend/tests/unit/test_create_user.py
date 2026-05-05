from unittest.mock import MagicMock
import pytest
from src.domain.entities.user import UserRole, UserStatus
from src.application.use_cases.create_user import CreateUserUseCase, CreateUserCommand
from src.infrastructure.persistence.memory_user_repo import InMemoryUserRepository
from src.infrastructure.messaging.noop_log_adapter import NoOpLogAdapter
from src.infrastructure.cache.noop_otp_adapter import NoOpOTPAdapter


@pytest.fixture
def use_case():
    return CreateUserUseCase(InMemoryUserRepository(), NoOpLogAdapter(), NoOpOTPAdapter())


def test_creates_user_with_pending_status(use_case):
    cmd = CreateUserCommand(
        name="João Silva", telephone="+5511999999999",
        email="joao@hospital.com.br", role=UserRole.SA_ROOT,
        performed_by="system", correlation_id="test-cid",
    )
    result = use_case.execute(cmd)

    assert result.user.uuid
    assert result.user.name == "João Silva"
    assert result.user.status == UserStatus.PENDING
    assert result.user.role == UserRole.SA_ROOT


def test_returns_otp_and_ttl(use_case):
    cmd = CreateUserCommand(
        name="A", telephone="+55", email="a@test.com",
        role=UserRole.SA_ROOT, performed_by="psa-uuid", correlation_id="cid",
    )
    result = use_case.execute(cmd)
    assert len(result.otp) == 6
    assert result.otp.isdigit()
    assert result.otp_ttl_seconds == 345_600  # 4 days


def test_rejects_duplicate_email(use_case):
    cmd = CreateUserCommand(
        name="A", telephone="+55", email="dup@test.com",
        role=UserRole.MEDICINER, performed_by="sa", correlation_id="cid",
    )
    use_case.execute(cmd)

    with pytest.raises(ValueError, match="already registered"):
        use_case.execute(cmd)


def test_publishes_log_event():
    log = MagicMock()
    uc = CreateUserUseCase(InMemoryUserRepository(), log, NoOpOTPAdapter())

    uc.execute(CreateUserCommand(
        name="B", telephone="+55", email="b@test.com",
        role=UserRole.SCHEDULER, performed_by="sa-uuid", correlation_id="cid-1",
    ))

    log.publish.assert_called_once()
    call_kwargs = log.publish.call_args.kwargs
    assert call_kwargs["action"] == "CREATE_USER"
    assert call_kwargs["correlation_id"] == "cid-1"
