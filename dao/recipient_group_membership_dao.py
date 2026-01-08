import logging
from typing import List, Optional

from dao.base_dao import BaseDao

logger = logging.getLogger(__name__)


class RecipientGroupMembershipDao(BaseDao):
    """DAO to manage recipient-group many-to-many memberships.

    Stores items with shape: {"recipient_id": int, "group_id": int}
    """
    def __init__(self, path: Optional[str] = None):
        super().__init__(path, data_name="recipient_group_membership")

    def list_group_members(self, group_id: int) -> List[int]:
        return [int(item.get('recipient_id')) for item in self._data.get(self.data_name, []) if int(item.get('group_id') or 0) == group_id]

    def list_recipient_groups(self, recipient_id: int) -> List[int]:
        return [int(item.get('group_id')) for item in self._data.get(self.data_name, []) if int(item.get('recipient_id') or 0) == recipient_id]

    def add_membership(self, recipient_id: int, group_id: int) -> bool:
        # avoid duplicates
        for item in self._data.get(self.data_name, []):
            if int(item.get('recipient_id') or 0) == recipient_id and int(item.get('group_id') or 0) == group_id:
                return False

        new_id = self._data.get('next_id', 1)
        entry = {"recipient_id": recipient_id, "group_id": group_id}
        self._data[self.data_name].append(entry)
        self._data['next_id'] = new_id + 1
        try:
            self.upsert_one(entry)
        except Exception:
            self._save()
        logger.info(f"[DAO] Added membership recipient={recipient_id} group={group_id}")
        return True

    def remove_membership(self, recipient_id: int, group_id: int) -> bool:
        before = len(self._data.get(self.data_name, []))
        self._data[self.data_name] = [it for it in self._data.get(self.data_name, []) if not (int(it.get('recipient_id') or 0) == recipient_id and int(it.get('group_id') or 0) == group_id)]
        if len(self._data[self.data_name]) < before:
            self._save()
            logger.info(f"[DAO] Removed membership recipient={recipient_id} group={group_id}")
            return True
        return False
