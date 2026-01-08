import logging

from typing import List, Optional

from dao.base_dao import BaseDao

from models.sender_model import SenderModel

logger = logging.getLogger(__name__)

class SenderDao(BaseDao):
    """
    DAO for managing email senders.

    Args:
        path (Optional[str]): Path to the JSON file for storing senders.
        data_name (str): Name of the data section in the JSON file.
    """
    def __init__(self, path: Optional[str] = None):
        super().__init__(path, data_name="senders")

    def list_all(self) -> List[SenderModel]:
        """
        List all email senders.

        Returns:
            List[SenderModel]: List of senders.
        """
        return [SenderModel(**s) for s in self._data[self.data_name]]

    def find_by_address(self, address: str) -> Optional[SenderModel]:
        """
        Find a sender by email address.

        Args:
            address (str): Email address to search for.
        Returns:
            Optional[SenderModel]: Sender data if found, else None.
        """
        for s in self._data[self.data_name]:
            if s["address"].lower() == address.lower():
                return SenderModel(**s)
        return None
    
    def find_by_id(self, sender_id: int) -> Optional[SenderModel]:
        """
        Find a sender by ID.

        Args:
            sender_id (int): ID of the sender to search for.
        Returns:
            Optional[SenderModel]: Sender data if found, else None.
        """
        for s in self._data[self.data_name]:
            if s["sender_id"] == sender_id:
                return SenderModel(**s)
        return None

    def add(self, sender: SenderModel) -> SenderModel:
        """
        Add a new sender.

        Args:
            sender (SenderModel): Sender data to add.
        Returns:
            SenderModel: The added sender data.
        """
        existing = self.find_by_address(sender.address)
        if existing:
            return existing
        
        new_id = self._data["next_id"]
        sender.sender_id = new_id

        self._data[self.data_name].append(sender.__dict__)

        self._data["next_id"] += 1

        try:
            self.upsert_one(sender.__dict__)
        except Exception:
            self._save()

        logger.info(f"[DAO] Added sender: {sender.address} (id={new_id})")

        return sender
    
    def edit(self, sender: SenderModel) -> SenderModel:
        """
        Edit an existing sender.

        Args:
            sender (SenderModel): Sender data to edit.
        Returns:
            SenderModel: The edited sender data.
        """
        for idx, s in enumerate(self._data[self.data_name]):
            if s["sender_id"] == sender.sender_id:
                self._data[self.data_name][idx] = sender.__dict__
                try:
                    self.upsert_one(sender.__dict__)
                except Exception:
                    self._save()

                logger.info(f"[DAO] Edited sender id={sender.sender_id}")

                return sender
        
        raise ValueError(f"Sender with id={sender.sender_id} not found.")

    def delete(self, sender_id: int) -> bool:
        """
        Delete a sender by ID.

        Args:
            sender_id (int): ID of the sender to delete.
        Returns:
            bool: True if the sender was deleted, False otherwise.
        """

        before = len(self._data[self.data_name])

        self._data[self.data_name] = [
            s for s in self._data[self.data_name] if s["sender_id"] != sender_id
        ]

        if len(self._data[self.data_name]) < before:
            self._save()

            logger.info(f"[DAO] Deleted sender id={sender_id}")

            return True
        
        return False
