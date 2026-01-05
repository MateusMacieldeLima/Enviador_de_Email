import keyring
from cryptography.fernet import Fernet, InvalidToken

DEFAULT_KEY_ID = "local-v1"
DEFAULT_SCHEME = "fernet:v1"

def get_default_key_id() -> str:
    """
    Get the default key ID.
    """
    return DEFAULT_KEY_ID

def get_default_scheme() -> str:
    """
    Get the default encryption scheme.
    """
    return DEFAULT_SCHEME

def generate_and_store_master_key(service_name: str, key_id: str = get_default_key_id()) -> bytes:
    """
    Generate a new Fernet master key and store it in the keyring.
    Args:
        service_name (str): The service name for the keyring.
        key_id (str): The identifier for the key.
    
    Returns:
        bytes: The generated master key.
    """

    try:
        if keyring.get_password(service_name, key_id):
            return

        key = Fernet.generate_key()
        keyring.set_password(service_name, key_id, key.decode())

        return key
    except Exception as e:
        raise RuntimeError(f"Failed to generate/store master key: {e}")

def __get_master_key(service_name: str, key_id: str = get_default_key_id()) -> bytes:
    """
    Retrieve the master key from the keyring.

    Args:
        service_name (str): The service name for the keyring.
        key_id (str): The identifier for the key.
    Returns:
        bytes: The master key.
    """
    
    key = keyring.get_password(service_name, key_id)

    if key is None:
        raise RuntimeError(f"Master key '{key_id}' not found in keyring")
    
    return key.encode()

def encrypt_password(service_name: str, plain: str, key_id: str = get_default_key_id()) -> str:
    """
    Encrypt a plain password using Fernet.

    Args:
        service_name (str): The service name for the keyring.
        plain (str): The plain password to encrypt.
        key_id (str): The identifier for the key.
    Returns:
        str: The encrypted password (Fernet token).
    """

    key = __get_master_key(service_name, key_id)
    f = Fernet(key)

    token = f.encrypt(plain.encode()).decode()

    return token

def decrypt_password(service_name: str, crypto_scheme: str, ciphertext: str, key_id: str = get_default_key_id()) -> str:
    """
    Decrypt an encrypted password using Fernet.

    Args:
        service_name (str): The service name for the keyring.
        crypto_scheme (str): The encryption scheme used.
        ciphertext (str): The encrypted password (Fernet token).
        key_id (str): The identifier for the key.
    Returns:
        str: The decrypted plain password.
    """
    if crypto_scheme != get_default_scheme():
        raise ValueError(f"Unsupported crypto scheme: {crypto_scheme}")
    
    key = __get_master_key(service_name, key_id)
    f = Fernet(key)

    return f.decrypt(ciphertext.encode()).decode()