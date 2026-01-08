import logging
import requests
import pandas as pd
import re

from typing import List, Optional

from dao.base_dao import BaseDao

from models.recipient_model import RecipientModel

from utils.files import file_exists

logger = logging.getLogger(__name__)

class RecipientDao(BaseDao):
    """
    DAO for managing email recipients.

    Args:
        path (Optional[str]): Path to the JSON file for storing recipients.
    
    """
    def __init__(self, path: Optional[str] = None):
        super().__init__(path, data_name="recipients", remote_only=True)

    def list_all(self) -> List[RecipientModel]:
        """
        List all recipients.

        Returns:
            List[RecipientModel]: List of recipients.
        """
        return [RecipientModel(**r) for r in self._data[self.data_name]]

    def find_by_address(self, address: str) -> Optional[RecipientModel]:
        """
        Find a recipient by email address.

        Args:
            address (str): Email address to search for.
        Returns:
            Optional[Dict[str, Any]]: Recipient data if found, else None.
        """
        for r in self._data[self.data_name]:
            if r["address"].lower() == address.lower():
                return RecipientModel(**r)
        return None

    def add(self, recipient: RecipientModel) -> RecipientModel:
        """
        Add a new recipient.

        Args:
            recipient (RecipientModel): Recipient data to add.
        Returns:
            RecipientModel: The added recipient data.
        """
        existing = self.find_by_address(recipient.address)
        if existing:
            return existing
        
        new_id = self._data["next_id"]
        recipient.recipient_id = new_id

        self._data[self.data_name].append(recipient.__dict__)

        self._data["next_id"] += 1

        # Try remote upsert only for this item to make manual UI inserts persist immediately
        try:
            self.upsert_one(recipient.__dict__)
        except Exception as e:
            # Log exception details, including HTTP response body when available
            try:
                logger.exception("Error upserting recipient %s: %s", recipient.address, e)
                if isinstance(e, requests.exceptions.RequestException) and hasattr(e, 'response') and e.response is not None:
                    logger.error('Upsert response status: %s', e.response.status_code)
                    logger.error('Upsert response text: %s', e.response.text)
            except Exception:
                pass

            # If remote reports a conflict (409), try reloading cache and return existing by address
            try:
                if isinstance(e, requests.exceptions.HTTPError) and getattr(e.response, 'status_code', None) == 409:
                    try:
                        self._load()
                        existing2 = self.find_by_address(recipient.address)
                        if existing2:
                            logger.info("[DAO] Conflict on add; using existing recipient for %s", recipient.address)
                            return existing2
                    except Exception:
                        pass
            except Exception:
                pass

            # fallback to full save
            self._save()

        logger.info(f"[DAO] Added recipient: {recipient.address} (id={new_id})")

        return recipient

    def update(self, recipient: RecipientModel) -> RecipientModel:
        """
        Update an existing recipient.

        Args:
            recipient (RecipientModel): Recipient data to update.
        Returns:
            RecipientModel: The updated recipient data.
        """
        for r in self._data[self.data_name]:
            if r["recipient_id"] == recipient.recipient_id:
                if recipient.address is not None:
                    r["address"] = recipient.address
                if recipient.group_id is not None:
                    r["group_id"] = recipient.group_id
                try:
                    self.upsert_one(r)
                except Exception:
                    self._save()
                return RecipientModel(**r)
        raise ValueError("Recipient not found")

    def delete(self, recipient_id: int) -> bool:
        """
        Delete a recipient by ID.

        Args:
            recipient_id (int): ID of the recipient to delete.
        Returns:
            bool: True if deleted, False otherwise.
        """
        
        before = len(self._data[self.data_name])

        self._data[self.data_name] = [
            r for r in self._data[self.data_name] if r["recipient_id"] != recipient_id
        ]

        if len(self._data[self.data_name]) < before:
            self._save()

            logger.info(f"[DAO] Deleted recipient id={recipient_id}")

            return True
        
        return False

    def extract_addresses_from_file(self, file_path: str) -> List[str]:
        """
        Extract email addresses from a CSV or Excel file.

        Args:
            file_path (str): Path to the CSV or Excel file.
        Returns:
            List[str]: List of extracted email addresses.
        """
        
        if not file_exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            if file_path.endswith(('.xls', '.xlsx')):
                logger.debug("[EXCEL] Reading Excel file...")
                df = pd.read_excel(file_path)
                logger.debug(f"[DATA] DataFrame created with {len(df)} rows and {len(df.columns)} columns")
            elif file_path.endswith('.csv'):
                logger.debug("[CSV] Reading CSV file...")
                df = pd.read_csv(file_path)
                logger.debug(f"[DATA] DataFrame created with {len(df)} rows and {len(df.columns)} columns")
            else:
                logger.error(f"[ERROR] Unsupported format: {file_path}")
                raise ValueError("Unsupported file format. Use .xlsx, .xls or .csv.")
        except FileNotFoundError:
            logger.error(f"[ERROR] File not found: {file_path}")
            raise FileNotFoundError(f"Error: The file '{file_path}' was not found.")
        except Exception as e:
            logger.error(f"[ERROR] Error reading file: {e}")
            raise Exception(f"Error reading file: {e}")

        regex_address = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        logger.debug(f"[REGEX] Email regex: {regex_address}")

        addresses: list[str] = []
        logger.debug(f"[PROCESS] Processing {len(df.columns)} columns...")

        for column in df.columns:
            logger.debug(f"[COLUMN] Processing column: {column}")
            for item in df[column]:
                try:
                    # Skip missing values
                    import pandas as _pd
                    if _pd.isna(item):
                        continue

                    # Coerce to string and search
                    text = str(item).strip()
                    if not text:
                        continue

                    # If cell contains common separators, split and check each
                    parts = re.split(r'[;,\|/\s]+', text)
                    found_any = []
                    for part in parts:
                        found = re.findall(regex_address, part)
                        if found:
                            found_any.extend(found)

                    # also search the whole cell as fallback
                    if not found_any:
                        found_any = re.findall(regex_address, text)

                    if found_any:
                        logger.debug(f"[EMAIL] Found addresses in '{text[:50]}...': {found_any}")
                    addresses.extend(found_any)
                except Exception:
                    # ignore problematic cells but continue
                    continue

        # Preserve duplicates and original discovery order so the import total
        # reflects the number of entries in the source file (user requirement).
        # Normalize to lowercase but keep duplicates.
        normalized = [e.lower() for e in addresses]
        logger.info(f"[EMAIL] Addresses found (including duplicates): {len(normalized)}")
        logger.debug(f"[EMAIL] Emails (first 10): {normalized[:10]}{'...' if len(normalized) > 10 else ''}")

        return normalized
