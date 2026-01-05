import logging
import sys

from PySide6.QtCore import QThread, Signal, Qt

from controller.email_controller import EmailController

from utils.exceptions import EmailServiceError

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('email_sender_debug.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class EmailWorker(QThread):
    """
    Thread for sending emails in the background.
    
    Args:
        controller: Instance of EmailController to handle email sending
        recipients: List of recipient email addresses
        subject: Subject of the email
        body: Body content of the email
        attachments: List of file paths to attach to the email
    """

    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, controller: EmailController, recipients: list[str], subject: str, body: str, attachments=None):
        super().__init__()

        self.controller = controller

        self.recipients = recipients
        self.subject = subject
        self.body = body
        self.attachments = attachments or []

        self._cancel_requested = False

        logger.debug(f"[EMAIL] EmailWorker criado para {len(recipients)} recipients")
        if self.attachments:
            logger.debug(f"[ANEXO] {len(self.attachments)} anexo(s) incluidos")
    
    def run(self):
        """
        Run the email sending process in the thread.
        """
        try:
            result = self.controller.send_mass_emails(
                self.recipients,
                self.subject,
                self.body,
                self.attachments,
                progress=self.progress,
                cancel_check=lambda: self._cancel_requested
            )

            if self._cancel_requested:
                logger.info("[ENVIO] Cancelamento solicitado pelo usuário")
                self.finished.emit(False, "Cancelado pelo usuário")
                return

            if result.get('canceled', False):
                self.finished.emit(False, "Envio cancelado pelo usuário")
            elif result['failed'] == 0:
                msg = 'Emails enviados com sucesso'
                self.finished.emit(True, msg)
            else:
                msg = f"{result['success']} enviados, {result['failed']} falharam"
                self.finished.emit(False, msg)
        except EmailServiceError as e:
            self.finished.emit(False, str(e))
        except Exception as e:
            self.finished.emit(False, f"Erro inesperado: {e}")

    def request_cancel(self):
        """
        Request cancellation of the email sending process.
        """
        self._cancel_requested = True
