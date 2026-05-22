import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def _send_smtp(to: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, [to], msg.as_string())


def _send_console(to: str, subject: str, html_body: str) -> None:
    logger.info(
        "\n" + "=" * 60 +
        f"\n[EMAIL] To: {to}\n[EMAIL] Subject: {subject}\n[EMAIL] Body:\n{html_body}\n" +
        "=" * 60
    )


def send_email(to: str, subject: str, html_body: str) -> None:
    if settings.EMAIL_BACKEND == "smtp":
        _send_smtp(to, subject, html_body)
    else:
        _send_console(to, subject, html_body)


def send_verification_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    html = f"""
    <h2>Vérifiez votre adresse email</h2>
    <p>Cliquez sur le lien ci-dessous pour activer votre compte :</p>
    <p><a href="{link}">{link}</a></p>
    <p>Ce lien expire dans 24 heures.</p>
    """
    send_email(to, "Confirmez votre email — Généalogie", html)


def send_reset_password_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    html = f"""
    <h2>Réinitialisation de mot de passe</h2>
    <p>Cliquez sur le lien ci-dessous pour choisir un nouveau mot de passe :</p>
    <p><a href="{link}">{link}</a></p>
    <p>Ce lien expire dans 30 minutes. Si vous n'avez pas fait cette demande, ignorez cet email.</p>
    """
    send_email(to, "Réinitialisation de mot de passe — Généalogie", html)
