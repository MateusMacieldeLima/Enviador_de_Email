import os
import smtplib
import mimetypes
import logging
import time

from models.email_model import EmailModel
from models.sender_model import SenderModel
from models.app_password_model import AppPasswordModel

from utils.exceptions import DailyLimitExceeded, RateLimitExceeded
from utils.fernet_crypto import decrypt_password

logger = logging.getLogger(__name__)

class EmailController:
    """
    Controller that handles email sending.

    Args:
        sender: SenderModel instance containing sender email details
    """
    def __init__(self, sender: SenderModel, app_password: AppPasswordModel):
        logger.info(f"[INIT] Initializing EmailController for: {sender.address}")

        self.sender = sender

        try:
            logger.debug("[DECRYPT] Decrypting application password...")
            # Support storing plaintext fallback (crypto_scheme == 'plain')
            if getattr(app_password, 'crypto_scheme', None) == 'plain':
                self.password = app_password.ciphertext
                logger.debug("[OK] Application password used as plain text")
            else:
                self.password = decrypt_password(
                    service_name="enviador_de_email",
                    crypto_scheme=app_password.crypto_scheme,
                    ciphertext=app_password.ciphertext,
                    key_id=app_password.key_id
                )
                logger.debug(f"[OK] Application password decrypted successfully")
        except Exception as e:
            logger.error(f"[ERROR] Failed to decrypt application password: {e}")
            raise
        
        logger.debug("[SMTP] Connecting to SMTP server...")
        self.smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        logger.debug("[OK] SMTP connection established")
        
        logger.debug("[AUTH] Logging in to SMTP server...")
        self.smtp_server.login(self.sender.address, self.password)
        logger.info("[OK] SMTP login successful")

    def send_mass_emails(self, recipient_list: list[str], subject: str, body: str, attachments: list | None = None, progress = None, cancel_check = None) -> dict:
        """
        Send emails in bulk to a list of recipients.
        
        Args:
            recipient_list: List of recipient email addresses
            subject: Subject of the email
            body: Body content of the email (HTML format)
            attachments: List of file paths to attach to the email
            progress: Optional callable to report progress (current, total)
            cancel_check: Optional callable that returns True if sending should be canceled

        Returns:
            A dictionary with counts of total, successful, and failed emails.
        """
        logger.info(f"[EMAIL] Starting bulk send to {len(recipient_list)} recipients")
        logger.debug(f"[EMAIL] Subject: {subject}")
        if attachments:
            logger.info(f"[ATTACHMENT] {len(attachments)} attachment(s) will be sent with each email")

        success_count = 0
        failed_count = 0

        try:
            for i, recipient in enumerate(recipient_list, 1):
                if cancel_check and cancel_check():
                    logger.info("[CANCEL] Email sending canceled by user")
                    return {
                        'total': len(recipient_list),
                        'success': success_count,
                        'failed': failed_count,
                        'canceled': True
                    }
                    
                logger.debug(f"[EMAIL] Sending email {i}/{len(recipient_list)} to: {recipient}")
                attempt = 0
                attempt_limit = 5
                sleep_time = 100

                for j in range(attempt_limit):
                    attempt += 1
                    try:
                        email = EmailModel(self.sender.address, recipient, subject, body, attachments)
                        result = self.send_email(email)
                        if result:
                            logger.debug(f"[OK] Email {i} sent successfully")
                            success_count += 1
                            progress.emit(i)
                            break
                    except RateLimitExceeded as rate_err:
                        logger.warning(f"[WARN] Rate limit exceeded when sending to: {recipient}: {rate_err}, trying again after delay. Attempt: {attempt}")
                        time.sleep(sleep_time)
                    except DailyLimitExceeded as daily_err:
                        logger.error(f"[ERROR] Daily limit exceeded when sending to: {recipient}: {daily_err}")
                        raise DailyLimitExceeded("[ERROR] Daily limit exceeded when sending to: {recipient}: {daily_err}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"[ERROR] Error sending email to {recipient}: {e}")
                        raise Exception(f"An error occurred sending email to {recipient}: {e}")
                        

            logger.info("[OK] All emails were sent successfully")
            logger.debug(f"[EMAIL] Bulk send results: {success_count} succeeded, {failed_count} failed")
            
            return {
                'total': len(recipient_list),
                'success': success_count,
                'failed': failed_count
            }
        except smtplib.SMTPAuthenticationError:
            logger.error("[ERROR] SMTP authentication error")
            raise ValueError("Authentication error! Check the email and app password.")
        except Exception as e:
            logger.error(f"[ERROR] Bulk send error: {e}")
            raise Exception(f"An error occurred: {e}")

    def send_email(self, email: EmailModel) -> bool:
        """
        Send a single email to a recipient.

        Args:
            email: EmailModel instance containing email details

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        
        if email.attachments:
            logger.debug(f"[ATTACHMENT] {len(email.attachments)} attachment(s) will be sent")

        try:
            msg = email.create_message()

            try:
                existing_attachments = []
                if msg.is_multipart():
                    for part in msg.iter_attachments():
                        existing_attachments.append(part)

                msg.clear_content()
                msg.set_content(email.body, subtype="html", charset="utf-8")

                for part in existing_attachments:
                    data = part.get_payload(decode=True)
                    ctype = part.get_content_type()
                    maintype, subtype = ctype.split("/", 1)
                    filename = part.get_filename()
                    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

                if not existing_attachments and email.attachments:
                    for path in email.attachments:
                        if not path:
                            continue
                        ctype, encoding = mimetypes.guess_type(path)
                        if ctype is None or encoding is not None:
                            ctype = "application/octet-stream"
                        maintype, subtype = ctype.split("/", 1)
                        with open(path, "rb") as f:
                            data = f.read()
                        msg.add_attachment(
                            data,
                            maintype=maintype,
                            subtype=subtype,
                            filename=os.path.basename(path),
                        )

                logger.debug("[EMAIL] Body forced to HTML and attachments consolidated")
            except Exception as adjust_err:
                logger.warning(f"[WARN] Could not adjust body to HTML: {adjust_err}. Sending as created by model.")

            logger.debug(f"[EMAIL] Sending message to: {email.recipient_address}")
            self.smtp_server.send_message(msg)
            logger.debug(f"[OK] Email sent successfully to: {email.recipient_address}")

            return True
        except smtplib.SMTPAuthenticationError:
            logger.error(f"[ERROR] Authentication error when sending to: {email.recipient_address}")
            raise ValueError("Authentication error! Check the email and app password.")
        except Exception as e:
            if "4.2.1" in str(e):
                raise RateLimitExceeded()
            elif "5.4.5" in str(e):
                raise DailyLimitExceeded()
            else:
                logger.error(f"[ERROR] Error sending email to {email.recipient_address}: {e}")
                raise Exception(f"An error occurred: {e}")

    def __del__(self):
        logger.debug("[SMTP] Closing SMTP connection...")
        try:
            self.smtp_server.quit()
        except Exception:
            pass
        logger.debug("[OK] SMTP connection closed")