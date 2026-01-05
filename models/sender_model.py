class SenderModel:
    """
    Model representing an email sender.

    Args:
        sender_id (int): Unique identifier for the sender.
        app_password (str): Application password for the sender's email account.
        app_password_id (int): Identifier for the associated app password record.
        address (str): Email address of the sender.
    """
    def __init__(self, sender_id: int = None, app_password_id: int = None, address: str = None):
        self.sender_id = sender_id
        self.app_password_id = app_password_id
        self.address = address
