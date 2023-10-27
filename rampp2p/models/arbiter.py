from django.db import models

from django.utils.crypto import get_random_string
from cryptography.fernet import Fernet
from django.conf import settings
import random

class Arbiter(models.Model):
    name = models.CharField(max_length=100)
    public_key = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    wallet_hash = models.CharField(
        max_length=100,
        unique=True
    )
    is_disabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True)

    auth_token = models.CharField(max_length=200, unique=True, null=True)
    auth_nonce = models.CharField(max_length=6, null=True)

    def create_auth_token(self):
        token = get_random_string(40)
        cipher_suite = Fernet(settings.FERNET_KEY)
        self.auth_token = cipher_suite.encrypt(token.encode()).decode()
        self.save()

    def update_auth_nonce(self):
        self.auth_nonce = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.save()

    def __str__(self):
        return self.name