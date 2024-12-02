from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


def encrypt_str(data:str, fernet_key:str=settings.STABLEHEDGE_FERNET_KEY):
    if isinstance(data, str): raise TypeError
    fernet_obj = Fernet(fernet_key)
    return fernet_obj.encrypt(data.encode()).decode()

def decrypt_str(data:str, fernet_key:str=settings.STABLEHEDGE_FERNET_KEY):
    if isinstance(data, str): raise TypeError
    fernet_obj = Fernet(fernet_key)
    return fernet_obj.decrypt(data.encode()).decode()

def decrypt_str_safe(data:str, fernet_key:str=settings.STABLEHEDGE_FERNET_KEY):
    try:
        return decrypt_str(data, fernet_key=fernet_key)
    except (TypeError, ValueError, InvalidToken):
        pass