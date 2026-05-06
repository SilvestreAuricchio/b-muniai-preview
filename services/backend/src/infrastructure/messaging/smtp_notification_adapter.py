import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.infrastructure.cache.noop_notification_adapter import NoOpNotificationAdapter

_log = logging.getLogger(__name__)


class SmtpNotificationAdapter(NoOpNotificationAdapter):
    """
    Extends the in-memory PSA inbox with real SMTP delivery for user-facing emails.

    Required env vars (same as SmtpOTPSender):
      SMTP_HOST, SMTP_USER, SMTP_PASSWORD
    Optional:
      SMTP_PORT (default 587), SMTP_FROM, APP_URL (default https://localhost)
    """

    def __init__(self, host: str, port: int, user: str, password: str, from_addr: str) -> None:
        super().__init__()
        self._host      = host
        self._port      = port
        self._user      = user
        self._password  = password
        self._from_addr = from_addr
        self._app_url   = os.environ.get("APP_URL", "https://localhost").rstrip("/")

    def send_activation_email(self, user_email: str, user_name: str, correlation_id: str) -> None:
        login_url = self._app_url

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "MuniAI — Your account is now active"
        msg["From"]    = self._from_addr
        msg["To"]      = user_email

        plain = (
            f"Hello {user_name},\n\n"
            "Your MuniAI account has been approved by an administrator. "
            "You can now sign in to the platform.\n\n"
            f"Sign in here: {login_url}\n\n"
            "Welcome to MuniAI!"
        )
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#f9fafb;margin:0;padding:32px">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;
              border:1px solid #e5e7eb;padding:40px">
    <h2 style="margin:0 0 8px;font-size:20px;color:#111827">Your account is active!</h2>
    <p style="margin:0 0 24px;color:#6b7280;font-size:14px">
      Hello <strong>{user_name}</strong>,<br><br>
      An administrator has approved your <strong>MuniAI</strong> account.
      You can now sign in and start using the platform.
    </p>

    <div style="text-align:center;margin:28px 0">
      <a href="{login_url}"
         style="display:inline-block;background:#dc2626;color:#fff;text-decoration:none;
                font-size:15px;font-weight:600;padding:14px 32px;border-radius:8px">
        Sign in to MuniAI
      </a>
    </div>

    <p style="margin:0;color:#9ca3af;font-size:12px;text-align:center">
      If you did not expect this email, please ignore it.
    </p>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        try:
            with smtplib.SMTP(self._host, self._port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(self._user, self._password)
                server.sendmail(self._from_addr, [user_email], msg.as_string())
            _log.info("Activation email sent → %s", user_email)
        except Exception as exc:
            _log.error("Failed to send activation email → %s: %s", user_email, exc)
