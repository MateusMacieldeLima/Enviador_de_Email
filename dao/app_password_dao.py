import logging

from typing import List, Optional

from dao.base_dao import BaseDao

from models.app_password_model import AppPasswordModel

from utils.fernet_crypto import encrypt_password, get_default_scheme, get_default_key_id

logger = logging.getLogger(__name__)

class AppPasswordDao(BaseDao):
    """
    DAO for managing email application passwords.

    Args:
        path (Optional[str]): Path to the JSON file for storing application passwords.
        data_name (str): Name of the data section in the JSON file.
    """
    def __init__(self, path: Optional[str] = None):
        super().__init__(path, data_name="app_passwords")

    def list_all(self) -> List[AppPasswordModel]:
        """
        List all application passwords.

        Returns:
            List[AppPasswordModel]: List of application passwords.
        """
        return [AppPasswordModel(**ap) for ap in self._data[self.data_name]]

    def find_by_id(self, app_password_id: int) -> Optional[AppPasswordModel]:
        """
        Find an application password by ID.

        Args:
            app_password_id (int): ID of the application password to search for.
        Returns:
            Optional[AppPasswordModel]: Application password data if found, else None.
        """
        for ap in self._data[self.data_name]:
            if ap["app_password_id"] == app_password_id:
                return AppPasswordModel(**ap)
        return None

    def add(self, app_password: AppPasswordModel) -> AppPasswordModel:
        """
        Add a new application password.

        Args:
            app_password (AppPasswordModel): Application password data to add.
        Returns:
            AppPasswordModel: The added application password data.
        """
        if app_password.ciphertext and not app_password.crypto_scheme:
            app_password.crypto_scheme = get_default_scheme()
            app_password.key_id = get_default_key_id()

            try:
                encrypted = encrypt_password("enviador_de_email", app_password.ciphertext, app_password.key_id)
                app_password.ciphertext = encrypted
            except Exception as e:
                # If encryption fails (e.g. master key missing in keyring),
                # fallback to storing the provided value as-is and mark scheme
                # as 'plain' so higher layers can detect it.
                logger.warning(f"[WARN] Encryption failed, storing plaintext fallback: {e}")
                app_password.crypto_scheme = "plain"
                app_password.key_id = None

        existing = self.find_by_id(app_password.app_password_id)
        if existing:
            if existing.ciphertext != app_password.ciphertext:
                existing.ciphertext = app_password.ciphertext
                existing.crypto_scheme = app_password.crypto_scheme
                existing.key_id = app_password.key_id
                self._save()
            return existing
        
        new_id = self._data["next_id"]
        app_password.app_password_id = new_id

        self._data[self.data_name].append(app_password.__dict__)

        self._data["next_id"] += 1

        try:
            self.upsert_one(app_password.__dict__)
        except Exception:
            self._save()

        logger.info(f"[DAO] Added app password: {app_password.ciphertext} (id={new_id})")

        return app_password

    def delete(self, app_password_id: int) -> bool:
        """
        Delete an application password by ID.

        Args:
            app_password_id (int): ID of the application password to delete.
        Returns:
            bool: True if the application password was deleted, False otherwise.
        """

        before = len(self._data[self.data_name])

        self._data[self.data_name] = [
            s for s in self._data[self.data_name] if s["app_password_id"] != app_password_id
        ]

        if len(self._data[self.data_name]) < before:
            self._save()

            logger.info(f"[DAO] Deleted app password id={app_password_id}")

            return True
        
        return False
