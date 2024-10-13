import os
import sys
import base64
from pathlib import Path
from cryptography.fernet import Fernet

HOME_DIR = str(Path.home())
SAGE_DIR = os.path.join(HOME_DIR, '.sage')
SECRET_KEY_FILE = os.path.join(SAGE_DIR, 'secret.key')
API_ENC_FILE = os.path.join(SAGE_DIR, 'api.enc')
API_KEY_HELP_FILE = '/usr/share/sage/Get_API_Key.txt'

def ensure_sage_setup():
    if not os.path.exists(SAGE_DIR):
        os.makedirs(SAGE_DIR, exist_ok=True)
    if not os.path.exists(SECRET_KEY_FILE) or os.path.getsize(SECRET_KEY_FILE) == 0:
        generate_key()
    if not os.path.exists(API_ENC_FILE) or os.path.getsize(API_ENC_FILE) == 0:
        return False
    return True

def generate_key():
    key = Fernet.generate_key()
    try:
        with open(SECRET_KEY_FILE, 'wb') as key_file:
            key_file.write(key)
    except Exception as e:
        print(f"Error saving encryption key: {e}")
        sys.exit(1)
    return key

def load_key():
    try:
        with open(SECRET_KEY_FILE, 'rb') as key_file:
            key = key_file.read()
            return key
    except Exception as e:
        print(f"Error loading encryption key: {e}")
        sys.exit(1)

def encrypt_api_key(api_key, key):
    f = Fernet(key)
    encrypted_key = f.encrypt(api_key.encode())
    try:
        with open(API_ENC_FILE, 'wb') as enc_file:
            enc_file.write(encrypted_key)
    except Exception as e:
        print(f"Error saving encrypted API key: {e}")
        sys.exit(1)

def decrypt_api_key(encrypted_key, key):
    f = Fernet(key)
    try:
        decrypted_key = f.decrypt(encrypted_key).decode()
        return decrypted_key
    except Exception as e:
        print(f"Error decrypting API key: {e}")
        sys.exit(1)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')