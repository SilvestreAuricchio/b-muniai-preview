import pytest
from src.domain.entities.user import UserRole, UserStatus
from src.application.use_cases.create_user import CreateUserUseCase, CreateUserCommand
from src.application.use_cases.activate_user import ActivateUserUseCase, ActivateUserCommand
from src.infrastructure.persistence.memory_user_repo import InMemoryUserRepository
from src.infrastructure.messaging.noop_log_adapter import NoOpLogAdapter


@pytest.fixture
def repo():
    return InMemoryUserRepository()


@pytest.fixture
def pending_user(repo):
    user = CreateUserUseCase(repo, NoOpLogAdapter()).execute(CreateUserCommand(
        name="Test", telephone="+55", email="t@test.com",
        role=UserRole.SA_ROOT, performed_by="system", correlation_id="cid",
    ))
    return user


def test_activates_pending_user(repo, pending_user):
    uc = ActivateUserUseCase(repo, NoOpLogAdapter())
    activated = uc.execute(ActivateUserCommand(
        uuid=pending_user.uuid, otp="123456",
        performed_by=pending_user.uuid, correlation_id="cid-2",
    ))
    assert activated.status == UserStatus.ACTIVE


def test_raises_for_unknown_uuid(repo):
    uc = ActivateUserUseCase(repo, NoOpLogAdapter())
    with pytest.raises(LookupError):
        uc.execute(ActivateUserCommand(
            uuid="nonexistent", otp="000000",
            performed_by="x", correlation_id="c",
        ))


def test_cannot_activate_twice(repo, pending_user):
    uc = ActivateUserUseCase(repo, NoOpLogAdapter())
    cmd = ActivateUserCommand(
        uuid=pending_user.uuid, otp="123456",
        performed_by=pending_user.uuid, correlation_id="c",
    )
    uc.execute(cmd)
    with pytest.raises(ValueError):
        uc.execute(cmd)
