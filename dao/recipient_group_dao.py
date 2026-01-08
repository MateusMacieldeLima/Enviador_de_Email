import logging
from typing import List, Optional
import logging
from typing import List, Optional

from dao.base_dao import BaseDao
from models.recipient_group_model import RecipientGroupModel

logger = logging.getLogger(__name__)


class RecipientGroupDao(BaseDao):
    """DAO for managing recipient groups.

    Uses `BaseDao` persistence layer. When remote is enabled, `BaseDao`
    handles communication with Supabase using the configured table_map.
    """
    def __init__(self, path: Optional[str] = None):
        super().__init__(path, data_name="groups")

    def list_all(self) -> List[RecipientGroupModel]:
        return [RecipientGroupModel(**g) for g in self._data[self.data_name]]

    def find_by_id(self, group_id: int) -> Optional[RecipientGroupModel]:
        for g in self._data[self.data_name]:
            if g.get("group_id") == group_id:
                return RecipientGroupModel(**g)
        return None

    def find_by_name(self, name: str) -> Optional[RecipientGroupModel]:
        for g in self._data[self.data_name]:
            if g.get("name") and g.get("name").lower() == name.lower():
                return RecipientGroupModel(**g)
        return None

    def add(self, group: RecipientGroupModel) -> RecipientGroupModel:
        existing = self.find_by_name(group.name)
        if existing:
            return existing

        new_id = self._data["next_id"]
        group.group_id = new_id

        self._data[self.data_name].append(group.__dict__)
        self._data["next_id"] += 1
        try:
            self.upsert_one(group.__dict__)
        except Exception:
            self._save()
        logger.info(f"[DAO] Added group: {group.name} (id={new_id})")
        return group

    def update(self, group: RecipientGroupModel) -> RecipientGroupModel:
        for g in self._data[self.data_name]:
            if g.get("group_id") == group.group_id:
                if group.group_id is not None:
                    g["group_id"] = group.group_id
                if group.name is not None:
                    g["name"] = group.name
                if group.recipients is not None:
                    g["recipients"] = group.recipients
                try:
                    self.upsert_one(g)
                except Exception:
                    self._save()
                return group
        raise ValueError("Group not found")

    def delete(self, group_id: int) -> bool:
        before = len(self._data[self.data_name])
        self._data[self.data_name] = [g for g in self._data[self.data_name] if g.get("group_id") != group_id]
        if len(self._data[self.data_name]) < before:
            self._save()
            logger.info(f"[DAO] Deleted group id={group_id}")
            return True
        return False

    def add_recipient_to_group(self, group_id: int, recipient_id: int) -> bool:
        g = self.find_by_id(group_id)
        if not g:
            raise ValueError("Group not found")
        if recipient_id not in g.recipients:
            g.recipients.append(recipient_id)
            self.update(g)
            logger.info(f"[DAO] Added recipient {recipient_id} to group {group_id}")
            return True
        return False

    def remove_recipient_from_group(self, group_id: int, recipient_id: int) -> bool:
        g = self.find_by_id(group_id)
        if not g:
            raise ValueError("Group not found")
        before = len(g.recipients)
        g.recipients = [rid for rid in g.recipients if rid != recipient_id]
        if len(g.recipients) < before:
            self.update(g)
            logger.info(f"[DAO] Removed recipient {recipient_id} from group {group_id}")
            return True
        return False
