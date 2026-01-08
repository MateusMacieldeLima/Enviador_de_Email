import logging

from typing import List

from dao.sender_dao import SenderDao
from dao.app_password_dao import AppPasswordDao

from models.sender_model import SenderModel
from models.app_password_model import AppPasswordModel 

from utils.exceptions import EmailServiceError

logger = logging.getLogger(__name__)

class SenderController:
    """
    Controller for managing email senders.

    Args:
        sender_dao (SenderDao): DAO for sender data management.
        app_password_dao (AppPasswordDao): DAO for app password management.
    """

    def __init__(self, sender_dao: SenderDao = None, app_password_dao: AppPasswordDao = None):
        self.sender_dao = sender_dao or SenderDao()
        self.app_password_dao = app_password_dao or AppPasswordDao()

        logger.info("[INIT] SenderController initialized")

    def add_sender(self, address: str, app_password: str) -> SenderModel:
        """
        Add a new sender.

        Args:
            address (str): Email address of the sender.
            app_password (str): App password for the sender email.

        Returns:
            SenderModel: The added sender data.
        """
        try:
            sender = self.sender_dao.add(SenderModel(address=address))

            ap = AppPasswordModel(ciphertext=app_password, sender_id=sender.sender_id)
            ap = self.app_password_dao.add(ap)

            sender.app_password_id = ap.app_password_id

            self.sender_dao.edit(sender)

            logger.info(f"[SERVICE] Sender persisted: {address}")

            return sender
        except Exception as e:
            logger.error(f"[ERRO] Erro ao adicionar remetente: {e}")

            raise EmailServiceError(f"Erro ao adicionar remetente: {e}")

    def list_senders(self) -> List[SenderModel]:
        """
        List all email senders.

        Returns:
            List[SenderModel]: List of senders.
        """
        return self.sender_dao.list_all()

    def delete_sender(self, sender_id: int) -> bool:
        """
        Delete a sender by its ID.
        
        Args:
            sender_id (int): ID of the sender to delete.

        Returns:
            bool: True if the sender was deleted, False otherwise.
        """

        try:
            sender = self.sender_dao.find_by_id(sender_id)
            if not sender:
                raise ValueError(f"Sender with id={sender_id} not found.")
            
            self.app_password_dao.delete(sender.app_password_id)
            
            return self.sender_dao.delete(sender_id)
        except Exception as e:
            logger.error(f"[ERRO] Erro ao deletar remetente: {e}")

            raise EmailServiceError(f"Erro ao deletar remetente: {e}")
        
    def get_password_for_sender(self, sender: SenderModel) -> AppPasswordModel:
        """
        Retrieve the app password for a given sender.

        Args:
            sender (SenderModel): The sender whose app password is to be retrieved.
        
        Returns:
            AppPasswordModel: The app password model for the sender.
        """
        # Defensive: if sender has no app_password_id, try to find by sender_id
        if not sender:
            return None

        if getattr(sender, 'app_password_id', None):
            ap = self.app_password_dao.find_by_id(sender.app_password_id)
            if ap:
                return ap

        # Fallback: search all app passwords for one matching sender_id
        try:
            for ap in self.app_password_dao.list_all():
                if getattr(ap, 'sender_id', None) == getattr(sender, 'sender_id', None):
                    return ap
        except Exception:
            pass

        return None
