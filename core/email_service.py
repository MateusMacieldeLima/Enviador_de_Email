import logging
from typing import List, Dict, Any, Optional


from dao.recipient_dao import RecipientDao
from dao.sender_dao import SenderDao
from dao.recipient_group_dao import RecipientGroupDao

from utils.exceptions import EmailServiceError

from controller.email_controller import EmailController
from controller.sender_controller import SenderController
from controller.recipient_controller import RecipientController
from controller.recipient_group_controller import RecipientGroupController

from models.sender_model import SenderModel

logger = logging.getLogger(__name__)

class EmailService:
    """
    Service that manages email sending operations and controllers.
    """

    def __init__(self):
        self.recipient_dao = RecipientDao()
        self.sender_dao = SenderDao()
        self.group_dao = RecipientGroupDao()

        self.email_controller: Optional[EmailController] = None
        self.sender_controller = SenderController(self.sender_dao)
        self.recipient_controller = RecipientController(self.recipient_dao, self.group_dao)
        self.group_controller = RecipientGroupController(self.recipient_dao, self.group_dao)

    def setup_email_controller(self, sender: SenderModel) -> bool:
        """
        Set up the email sender.

        Args:
            sender: SenderModel instance with sender email details

        Returns:
            True if configuration is successful, raises EmailServiceError otherwise.
        """
        logger.info(f"[CONFIG] Configurando remetente: {sender.address}")
        try:
            app_password = self.sender_controller.get_password_for_sender(sender)
            self.email_controller = EmailController(sender, app_password)
            logger.info("[OK] Remetente configurado com sucesso")
            return True
        except Exception as e:
            logger.error(f"[ERRO] Erro ao configurar remetente: {e}")
            raise EmailServiceError(f"Erro ao configurar remetente: {e}")
    

    

