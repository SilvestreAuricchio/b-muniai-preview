import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.application.ports.otp_sender_port import OTPSenderPort, PermanentDeliveryError

_log = logging.getLogger(__name__)


def _ttl_label(ttl_seconds: int) -> str:
    days  = ttl_seconds // 86_400
    hours = (ttl_seconds % 86_400) // 3_600
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''}"
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{ttl_seconds // 60} minutes"


class SmtpOTPSender(OTPSenderPort):
    """
    Sends OTP via SMTP (STARTTLS).

    Required env vars:
      SMTP_HOST      — e.g. smtp.gmail.com
      SMTP_USER      — login / sender address
      SMTP_PASSWORD  — app-specific password

    Optional:
      SMTP_PORT      — default 587
      SMTP_FROM      — display address (defaults to SMTP_USER)
      APP_URL        — base URL for activation link (default https://localhost)
    """

    def __init__(self, host: str, port: int, user: str, password: str, from_addr: str) -> None:
        self._host      = host
        self._port      = port
        self._user      = user
        self._password  = password
        self._from_addr = from_addr
        self._app_url   = os.environ.get("APP_URL", "https://localhost").rstrip("/")

    def send(self, uuid: str, email: str, telephone: str, otp: str, ttl_seconds: int) -> None:
        ttl          = _ttl_label(ttl_seconds)
        activate_url = f"{self._app_url}/activate/{uuid}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "MuniAI — Your verification code"
        msg["From"]    = self._from_addr
        msg["To"]      = email

        plain = (
            f"Your MuniAI verification code is: {otp}\n\n"
            f"Activate your account here:\n{activate_url}\n\n"
            f"This code is valid for {ttl}.\n"
            "Do not share it with anyone."
        )
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#f9fafb;margin:0;padding:32px">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;
              border:1px solid #e5e7eb;padding:40px">
    <h2 style="margin:0 0 8px;font-size:20px;color:#111827">You have been invited to MuniAI</h2>
    <p style="margin:0 0 24px;color:#6b7280;font-size:14px">
      Use the code below or click the button to activate your account.
    </p>

    <!-- OTP code -->
    <div style="text-align:center;background:#f3f4f6;border-radius:8px;padding:24px 0;
                letter-spacing:0.35em;font-size:36px;font-weight:700;color:#111827">
      {otp}
    </div>

    <!-- Activation button -->
    <div style="text-align:center;margin:28px 0">
      <a href="{activate_url}"
         style="display:inline-block;background:#dc2626;color:#fff;text-decoration:none;
                font-size:15px;font-weight:600;padding:14px 32px;border-radius:8px">
        Activate my account
      </a>
    </div>

    <p style="margin:0;color:#9ca3af;font-size:12px;text-align:center">
      Valid for {ttl}&nbsp;&nbsp;·&nbsp;&nbsp;Do not share this code with anyone.
    </p>

    <hr style="border:none;border-top:1px solid #f3f4f6;margin:24px 0">
    <p style="margin:0;color:#d1d5db;font-size:11px;text-align:center;word-break:break-all">
      {activate_url}
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
                server.sendmail(self._from_addr, [email], msg.as_string())
        except smtplib.SMTPAuthenticationError as exc:
            raise PermanentDeliveryError(
                f"SMTP auth failed for {self._user} — check SMTP_PASSWORD in .env: {exc}"
            ) from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise PermanentDeliveryError(f"Recipient refused {email}: {exc}") from exc

        _log.info("OTP email sent → %s  activate_url=%s", email, activate_url)
