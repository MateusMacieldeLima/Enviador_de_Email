class AppPasswordModel:
    """
    Model representing an application password with encryption details.

    Args:
        app_password_id (int): Unique identifier for the app password.
        sender_id (int): Identifier for the associated sender.
        ciphertext (str): Encrypted application password.
        crypto_scheme (str): Encryption scheme used.
        key_id (str): Identifier for the encryption key.
    """
    def __init__(self, app_password_id: int = None, sender_id: int = None, ciphertext: str = None, crypto_scheme: str = None, key_id: str = None):
        self.app_password_id = app_password_id
        self.sender_id = sender_id
        self.ciphertext = ciphertext
        self.crypto_scheme = crypto_scheme
        self.key_id = key_id