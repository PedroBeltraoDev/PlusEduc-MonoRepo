import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.smtp_username and self._settings.smtp_password)

    def send_password_reset_code(self, *, account_email: str, code: str) -> None:
        recipient = self._settings.password_reset_override_email or account_email
        from_email = self._settings.smtp_from_email or self._settings.smtp_username

        message = EmailMessage()
        message["Subject"] = "PlusEduc - Código de recuperação de senha"
        message["From"] = f"{self._settings.smtp_from_name} <{from_email}>"
        message["To"] = recipient

        override_note = (
            f"\n\n(Solicitado pela conta: {account_email})" if recipient != account_email else ""
        )
        message.set_content(
            "Recebemos um pedido de redefinição de senha para a conta "
            f"{account_email} no PlusEduc.\n\n"
            f"Código de verificação: {code}\n"
            f"Este código expira em {self._settings.password_reset_code_ttl_minutes} minutos.\n\n"
            "Se você não solicitou isso, ignore este e-mail." + override_note
        )

        if not self.is_configured:
            logger.warning(
                "SMTP não configurado; código de recuperação não foi enviado por e-mail "
                "(conta=%s, código=%s)",
                account_email,
                code,
            )
            return

        try:
            with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self._settings.smtp_username, self._settings.smtp_password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as error:
            logger.error("Falha ao enviar e-mail de recuperação de senha: %s", error)
            raise EmailDeliveryError("Não foi possível enviar o e-mail de recuperação") from error
