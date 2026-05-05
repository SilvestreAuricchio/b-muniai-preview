"""
Two-phase activation tests:
  Phase 3a — invitee verifies OTP → pending_approval  (VerifyOTPUseCase)
  Phase 3b — PSA approves          → active            (ApproveUserUseCase)
"""
import pytest
from src.domain.entities.user import UserRole, UserStatus
from src.application.use_cases.create_user import CreateUserUseCase, CreateUserCommand
from src.application.use_cases.verify_otp import VerifyOTPUseCase, VerifyOTPCommand
from src.application.use_cases.approve_user import ApproveUserUseCase, ApproveUserCommand
from src.infrastructure.persistence.memory_user_repo import InMemoryUserRepository
from src.infrastructure.messaging.noop_log_adapter import NoOpLogAdapter
from src.infrastructure.cache.noop_otp_adapter import NoOpOTPAdapter
from src.infrastructure.cache.noop_notification_adapter import NoOpNotificationAdapter


@pytest.fixture
def repo():
    return InMemoryUserRepository()

@pytest.fixture
def challenge():
    return NoOpOTPAdapter()

@pytest.fixture
def notification():
    return NoOpNotificationAdapter()

@pytest.fixture
def create_uc(repo, challenge):
    return CreateUserUseCase(repo, NoOpLogAdapter(), challenge)

@pytest.fixture
def verify_uc(repo, challenge, notification):
    return VerifyOTPUseCase(repo, NoOpLogAdapter(), challenge, notification)

@pytest.fixture
def approve_uc(repo):
    return ApproveUserUseCase(repo, NoOpLogAdapter())

@pytest.fixture
def pending(create_uc):
    return create_uc.execute(CreateUserCommand(
        name="Test", telephone="+55", email="t@test.com",
        role=UserRole.SA_ROOT, performed_by="psa-uuid", correlation_id="cid",
    ))


# ── Phase 3a: OTP verification ────────────────────────────────────────────

def test_otp_verify_transitions_to_pending_approval(verify_uc, pending):
    user = verify_uc.execute(VerifyOTPCommand(
        uuid=pending.user.uuid, otp=pending.otp, correlation_id="cid-v",
    ))
    assert user.status == UserStatus.PENDING_APPROVAL


def test_otp_verify_raises_for_unknown_uuid(verify_uc):
    with pytest.raises(LookupError):
        verify_uc.execute(VerifyOTPCommand(uuid="nope", otp="000000", correlation_id="c"))


def test_otp_verify_raises_for_wrong_otp(verify_uc, pending):
    with pytest.raises(ValueError, match="Invalid or expired OTP"):
        verify_uc.execute(VerifyOTPCommand(
            uuid=pending.user.uuid, otp="000000", correlation_id="c",
        ))


def test_otp_verify_notifies_psa(verify_uc, pending, notification):
    verify_uc.execute(VerifyOTPCommand(
        uuid=pending.user.uuid, otp=pending.otp, correlation_id="cid-n",
    ))
    events = notification.pop_for_psa("psa-uuid")
    assert len(events) == 1
    assert events[0]["type"] == "USER_OTP_VERIFIED"


# ── Phase 3b: PSA approval ────────────────────────────────────────────────

def test_approve_activates_pending_approval_user(verify_uc, approve_uc, pending):
    verify_uc.execute(VerifyOTPCommand(
        uuid=pending.user.uuid, otp=pending.otp, correlation_id="cid-v",
    ))
    user = approve_uc.execute(ApproveUserCommand(
        uuid=pending.user.uuid, performed_by="psa-uuid", correlation_id="cid-a",
    ))
    assert user.status == UserStatus.ACTIVE


def test_approve_raises_if_otp_not_verified(approve_uc, pending):
    with pytest.raises(ValueError, match="OTP must be verified first"):
        approve_uc.execute(ApproveUserCommand(
            uuid=pending.user.uuid, performed_by="psa-uuid", correlation_id="c",
        ))


def test_approve_raises_for_unknown_uuid(approve_uc):
    with pytest.raises(LookupError):
        approve_uc.execute(ApproveUserCommand(uuid="nope", performed_by="p", correlation_id="c"))
