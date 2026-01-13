from datetime import datetime, timezone
from typing import Optional

import structlog

from src.config import settings
from src.storage import Digest, SessionLocal

logger = structlog.get_logger()


class EmailSender:
    def __init__(self):
        self.sg_client = None
        if settings.sendgrid_api_key:
            try:
                from sendgrid import SendGridAPIClient
                self.sg_client = SendGridAPIClient(settings.sendgrid_api_key)
            except ImportError:
                logger.warning("sendgrid_not_installed")

    def send_digest(self, digest: Digest, to_email: Optional[str] = None) -> bool:
        if not self.sg_client:
            logger.error("sendgrid_not_configured")
            return False

        recipient = to_email or settings.to_email
        if not recipient:
            logger.error("no_recipient_email")
            return False

        from sendgrid.helpers.mail import Mail, Email, To, Content as SGContent

        date_str = digest.date.strftime("%B %d, %Y")
        subject = f"AI News Digest - {date_str}"

        message = Mail(
            from_email=Email(settings.from_email),
            to_emails=To(recipient),
            subject=subject,
            html_content=SGContent("text/html", digest.html_content),
        )

        try:
            response = self.sg_client.send(message)
            
            if response.status_code in [200, 201, 202]:
                with SessionLocal() as session:
                    db_digest = session.query(Digest).filter_by(id=digest.id).first()
                    if db_digest:
                        db_digest.sent = True
                        db_digest.sent_at = datetime.now(timezone.utc)
                        session.commit()
                
                logger.info(
                    "digest_sent",
                    digest_id=digest.id,
                    recipient=recipient,
                    status=response.status_code,
                )
                return True
            else:
                logger.error(
                    "send_failed",
                    status=response.status_code,
                    body=response.body,
                )
                return False

        except Exception as e:
            logger.error("send_exception", error=str(e))
            return False

    def send_latest_digest(self, to_email: Optional[str] = None) -> bool:
        with SessionLocal() as session:
            digest = (
                session.query(Digest)
                .filter_by(sent=False)
                .order_by(Digest.created_at.desc())
                .first()
            )
            
            if not digest:
                logger.info("no_unsent_digest")
                return False

            return self.send_digest(digest, to_email)
