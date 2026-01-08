import logging

from typing import List

from dao.recipient_dao import RecipientDao
from dao.recipient_group_dao import RecipientGroupDao
from dao.recipient_group_membership_dao import RecipientGroupMembershipDao

from models.recipient_model import RecipientModel

from utils.exceptions import EmailServiceError

logger = logging.getLogger(__name__)

class RecipientController:
    """
    Controller for managing email recipients.

    Args:
        recipient_dao (RecipientDao): DAO for recipients.
        group_dao (RecipientGroupDao): DAO for recipient groups.
    """

    def __init__(self, recipient_dao: RecipientDao = None, group_dao: RecipientGroupDao = None):
        self.recipient_dao = recipient_dao or RecipientDao()
        self.group_dao = group_dao or RecipientGroupDao()
        self.membership_dao = RecipientGroupMembershipDao()

        logger.info("[INIT] RecipientController initialized")

    def add_recipient(self, address: str, group_id: int = 0) -> RecipientModel:
        """
        Add a new recipient.

        Args:
            address (str): Email address of the recipient.
            group_id (int): ID of the recipient group.
        Returns:
            RecipientModel: The added recipient data.
        """

        try:
            rec = RecipientModel(address=address, group_id=group_id)
            rec = self.recipient_dao.add(rec)
            logger.info(f"[SERVICE] Recipient added: {address}")

            if group_id and rec and isinstance(rec, RecipientModel) and rec.recipient_id is not None:
                # Prefer membership table for many-to-many; fallback to legacy group list
                try:
                    try:
                        self.membership_dao.add_membership(rec.recipient_id, group_id)
                    except Exception:
                        # fallback to legacy behavior
                        self.group_dao.add_recipient_to_group(group_id, rec.recipient_id)
                except Exception as grp_err:
                    logger.warning(f"[WARN] Falha ao associar recipient {rec.recipient_id} ao grupo {group_id}: {grp_err}")

            return rec
        except Exception as e:
            # Log detailed info including HTTP response when available
            try:
                logger.exception("[ERRO] Erro ao adicionar destinatario %s: %s", address, e)
                if hasattr(e, 'response') and e.response is not None:
                    logger.error('Response status: %s', e.response.status_code)
                    logger.error('Response text: %s', e.response.text)
            except Exception:
                pass
            raise EmailServiceError(f"Erro ao adicionar destinatario: {e}")

    def list_recipients(self) -> List[RecipientModel]:
        """
        List all email recipients.
        Returns:
            List[RecipientModel]: List of recipients.
        """

        return self.recipient_dao.list_all()
    
    def update_recipient(self, recipient_id: int, address: str | None = None, group_id: int | None = None) -> RecipientModel:
        """
        Update an existing recipient.

        Args:
            recipient_id (int): ID of the recipient to update.
            address (Optional[str]): New email address.
            group_id (Optional[int]): New group ID.
        Returns:
            RecipientModel: The updated recipient data.
        """
        
        try:
            recipient = RecipientModel(recipient_id=recipient_id, address=address, group_id=group_id)
            return self.recipient_dao.update(recipient)
        except Exception as e:
            logger.error(f"[ERRO] Erro ao atualizar destinatario: {e}")
            raise EmailServiceError(f"Erro ao atualizar destinatario: {e}")


    def delete_recipient(self, recipient_id: int) -> bool:
        """
        Delete a recipient by ID.

        Args:
            recipient_id (int): ID of the recipient to delete.
        Returns:
            bool: True if the recipient was deleted, False otherwise.
        """

        try:
            return self.recipient_dao.delete(recipient_id)
        except Exception as e:
            logger.error(f"[ERRO] Erro ao deletar destinatario: {e}")

            raise EmailServiceError(f"Erro ao deletar destinatario: {e}")


    def process_recipient_file(self, file_path: str) -> List[str]:
        """
        Process a file to extract recipient email addresses.

        Args:
            file_path (str): Path to the file.
        Returns:
            List[str]: List of extracted email addresses.
        """

        logger.info(f"[FILE] Processando arquivo: {file_path}")

        try:
            addresses = self.recipient_dao.extract_addresses_from_file(file_path)

            if not addresses:
                logger.warning("[WARN] Nenhum email valido encontrado no arquivo")
                raise EmailServiceError("Nenhum email válido encontrado no arquivo")
            
            logger.info(f"[FILE] Emails extraidos: {addresses}")
            
            return addresses
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"[ERRO] Erro ao processar arquivo: {e}")

            raise EmailServiceError(f"Erro ao processar arquivo: {e}")