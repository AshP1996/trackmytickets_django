"""
Encryption utilities for securely storing database credentials
"""
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os

def get_encryption_key():
    """
    Get or generate encryption key for credentials
    """
    # Try to get from environment variable
    key = os.environ.get('DB_CREDENTIALS_ENCRYPTION_KEY')
    
    if not key:
        # Try to get from settings
        key = getattr(settings, 'DB_CREDENTIALS_ENCRYPTION_KEY', None)
    
    if not key:
        # Generate a new key (for development only)
        # In production, this should be set in environment variables
        key = Fernet.generate_key().decode()
        print(f"WARNING: Generated new encryption key. Set DB_CREDENTIALS_ENCRYPTION_KEY in environment: {key}")
    
    if isinstance(key, str):
        key = key.encode()
    
    return key

def encrypt_password(raw_password):
    """
    Encrypt a password using Fernet symmetric encryption
    """
    if not raw_password:
        return None
    
    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(raw_password.encode())
    return base64.b64encode(encrypted).decode()

def decrypt_password(encrypted_password):
    """
    Decrypt a password
    """
    if not encrypted_password:
        return None
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_password.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        print(f"Error decrypting password: {e}")
        return None
