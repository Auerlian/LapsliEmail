from cryptography.fernet import Fernet
import base64
import hashlib

class CredentialEncryption:
    def __init__(self, key: str):
        key_bytes = hashlib.sha256(key.encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_bytes))
    
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()
