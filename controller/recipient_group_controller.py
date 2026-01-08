import logging

from typing import List

from dao.recipient_group_dao import RecipientGroupDao
from dao.recipient_dao import RecipientDao
from dao.recipient_group_membership_dao import RecipientGroupMembershipDao

from models.recipient_model import RecipientModel
from models.recipient_group_model import RecipientGroupModel

from utils.exceptions import EmailServiceError
from dao import supabase_client

logger = logging.getLogger(__name__)


class RecipientGroupController:
    """
    Controller for managing recipient groups.

    Args:
        recipient_dao (RecipientDao): DAO for recipients.
        group_dao (RecipientGroupDao): DAO for recipient groups.
    """

    def __init__(self, recipient_dao: RecipientDao = None, group_dao: RecipientGroupDao = None):
        self.recipient_dao = recipient_dao or RecipientDao()
        self.group_dao = group_dao or RecipientGroupDao()
        self.membership_dao = RecipientGroupMembershipDao()

        logger.info("[INIT] RecipientGroupController initialized")

    def add_group(self, name: str) -> RecipientGroupModel:
        """
        Add a new recipient group.

        Args:
            name (str): Name of the group.
        Returns:
            RecipientGroupModel: The added group data.
        """

        try:
            group = RecipientGroupModel(name=name)

            grp = self.group_dao.add(group)

            logger.info(f"[SERVICE] Group added: {name}")

            return grp
        except Exception as e:
            logger.error(f"[ERRO] Erro ao adicionar grupo: {e}")
            raise EmailServiceError(str(e))

    def list_groups(self) -> List[RecipientGroupModel]:
        """
        List all recipient groups.

        Returns:
            List[RecipientGroupModel]: List of recipient groups.
        """
        return self.group_dao.list_all()

    def delete_group(self, group_id: int) -> bool:
        """
        Delete a recipient group.

        Args:
            group_id (int): ID of the group to delete.
        Returns:
            bool: True if deleted, False otherwise.
        """
        try:
            # gather members via membership table first (if available), else derive from recipients
            try:
                member_ids = self.membership_dao.list_group_members(group_id)
            except Exception:
                member_ids = [r.recipient_id for r in self.recipient_dao.list_all() if getattr(r, 'group_id', None) == group_id]

            # remove membership entries (local + remote)
            for rid in list(member_ids):
                try:
                    try:
                        self.membership_dao.remove_membership(rid, group_id)
                    except Exception:
                        pass
                    try:
                        supabase_client.delete_by_filters(self.membership_dao._table, {'recipient_id': rid, 'group_id': group_id})
                    except Exception:
                        pass
                except Exception:
                    logger.warning(f"[WARN] Não foi possível remover membership recipient={rid} group={group_id}")

            # delete recipients that are only in this group (i.e., no other membership entries)
            for rid in list(member_ids):
                try:
                    other_groups = self.membership_dao.list_recipient_groups(rid)
                    # if membership table empty or only contains this group, remove recipient
                    if not other_groups or all(int(gid) == int(group_id) for gid in other_groups):
                        try:
                            self.recipient_dao.delete(rid)
                        except Exception:
                            pass
                        try:
                            supabase_client.delete_row(self.recipient_dao._table, 'recipient_id', rid)
                        except Exception:
                            pass
                except Exception:
                    logger.warning(f"[WARN] Falha ao avaliar exclusao de recipient {rid}")

            # finally delete the group itself (local + remote)
            deleted = self.group_dao.delete(group_id)
            try:
                supabase_client.delete_row(self.group_dao._table, 'group_id', group_id)
            except Exception:
                pass

            if deleted:
                logger.info(f"[SERVICE] Grupo {group_id} deletado e membros removidos")

            return deleted
        except Exception as e:
            logger.error(f"[ERRO] Erro ao deletar grupo: {e}")

            raise EmailServiceError(str(e))

    def add_recipient_to_group(self, recipient_id: int, group_id: int) -> bool:
        """
        Add a recipient to a group.

        Args:
            recipient_id (int): ID of the recipient to add.
            group_id (int): ID of the group.
        Returns:
            bool: True if added, False otherwise.
        """
        try:
            # Prefer using the membership table for many-to-many relationships.
            try:
                added = self.membership_dao.add_membership(recipient_id, group_id)
                if added:
                    return True
                return False
            except Exception:
                # If membership table not available (schema not applied), fallback to legacy behavior
                logger.warning("[WARN] Membership table unavailable; falling back to legacy single-group behavior")

            # Legacy fallback: assign recipient.group_id and ensure group's recipients list
            existing = next((r for r in self.recipient_dao.list_all() if r.recipient_id == recipient_id), None)
            if existing:
                if existing.group_id == group_id:
                    # ensure group has the recipient id in its list
                    try:
                        self.group_dao.add_recipient_to_group(group_id, recipient_id)
                    except Exception:
                        logger.warning(f"[WARN] Falha ao adicionar recipient {recipient_id} à lista do grupo {group_id}")
                    return True
                existing.group_id = group_id
                try:
                    self.recipient_dao.update(existing)
                except Exception:
                    try:
                        self.recipient_dao._load()
                        existing2 = next((r for r in self.recipient_dao.list_all() if r.recipient_id == recipient_id), None)
                        if existing2:
                            existing2.group_id = group_id
                            try:
                                self.recipient_dao.update(existing2)
                            except Exception:
                                logger.warning(f"[WARN] Não foi possível atualizar group_id do recipient {recipient_id}, seguindo com associação de grupo")
                    except Exception:
                        logger.warning(f"[WARN] Falha ao recarregar destinatarios após erro ao atualizar recipient {recipient_id}")

            recipient = RecipientModel(recipient_id=recipient_id, group_id=group_id)
            try:
                self.recipient_dao.update(recipient)
            except Exception:
                logger.warning(f"[WARN] Falha ao atualizar recipient {recipient_id}; tentando apenas associar ao grupo")
            try:
                self.group_dao.add_recipient_to_group(group_id, recipient_id)
            except Exception as e:
                logger.error(f"[ERRO] Falha ao adicionar recipient {recipient_id} ao grupo {group_id}: {e}")
                raise EmailServiceError(str(e))

            return True
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"[ERRO] Erro ao adicionar recipient {recipient_id} ao grupo {group_id}: {e}")
            raise EmailServiceError(str(e))


    def list_group_recipients(self, group_id: int) -> List[RecipientModel]:
        """
        List all recipients in a group.

        Args:
            group_id (int): ID of the group.
        Returns:
            List[RecipientModel]: List of recipients in the group.
        """

        # Prefer deriving group membership from recipients' `group_id` field
        # as it is the single source of truth and avoids inconsistencies
        # when the group's `recipients` array isn't persisted or updated.
        # Validate group exists for API consistency.
        grp = self.group_dao.find_by_id(group_id)
        if not grp:
            raise EmailServiceError("Grupo não encontrado")

        # First try membership table (many-to-many)
        try:
            member_ids = self.membership_dao.list_group_members(group_id)
            if member_ids:
                members = []
                all_recipients = {r.recipient_id: r for r in self.recipient_dao.list_all()}
                for rid in member_ids:
                    r = all_recipients.get(int(rid))
                    if r:
                        members.append(r)
                return members
        except Exception:
            # ignore and fallback
            pass

        # Fallback: derive membership from recipients' `group_id` field
        members = [r for r in self.recipient_dao.list_all() if getattr(r, 'group_id', None) == group_id]
        return members

    