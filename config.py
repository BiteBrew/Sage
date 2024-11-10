# config.py

import json
import os
from pathlib import Path
from utils import ensure_sage_setup, load_key, decrypt_api_key, encrypt_api_key
import sys
import subprocess

HOME_DIR = str(Path.home())
SAGE_DIR = os.path.join(HOME_DIR, '.sage')
USER_CONFIG_FILE = os.path.join(SAGE_DIR, 'config.json')
SYSTEM_CONFIG_FILE = '/etc/sage/config.json'
MODELS_FILE = '/etc/sage/models.json'
API_ENC_FILE = os.path.join(SAGE_DIR, 'api.enc')  # Add this line
API_KEY_HELP_FILE = "path/to/api_key_help.txt"

DEFAULT_OPTIONS = {
    'model': 'llama3.2',
    'model_provider': 'ollama',
    'temperature': 0.3,
    'max_tokens': 1500,
    'context_window_size': 10,
    'terminal_emulator': 'gnome-terminal'
}

DEFAULT_AVAILABLE_MODELS = [
    "gpt-4o-mini",  # Preferred OpenAI model
    "gpt-4o"        # Full version available but not default
]

def get_default_model():
    """Determine the default model based on Ollama availability"""
    try:
        ollama_models = get_ollama_models()
        if 'llama3.2:latest' in ollama_models:
            return ('llama3.2:latest', 'ollama')
        return ('gpt-4o-mini', 'openai')
    except:
        return ('gpt-4o-mini', 'openai')

# Update DEFAULT_OPTIONS to use the determined default model
default_model, default_provider = get_default_model()
DEFAULT_OPTIONS = {
    'model': default_model,
    'model_provider': default_provider,
    'temperature': 0.3,
    'max_tokens': 1500,
    'context_window_size': 10,
    'terminal_emulator': 'gnome-terminal'
}

def load_options():
    """
    Load user-specific options, then system-wide options, and finally default options.
    User settings override system settings.
    """
    options = DEFAULT_OPTIONS.copy()

    # Load system-wide options
    if os.path.exists(SYSTEM_CONFIG_FILE):
        try:
            with open(SYSTEM_CONFIG_FILE, 'r') as f:
                system_options = json.load(f)
            options.update(system_options)
        except json.JSONDecodeError as e:
            print(f"Error loading system options: {e}")

    # Load user-specific options
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r') as f:
                user_options = json.load(f)
            options.update(user_options)
        except json.JSONDecodeError as e:
            print(f"Error loading user options: {e}")

    # Ensure all default options are present
    for key, value in DEFAULT_OPTIONS.items():
        options.setdefault(key, value)

    return options

def save_options(options):
    """
    Save user-specific options to the user configuration file.
    """
    try:
        os.makedirs(SAGE_DIR, exist_ok=True)
        with open(USER_CONFIG_FILE, 'w') as f:
            json.dump(options, f, indent=4)
        print("Options saved successfully.")
    except Exception as e:
        print(f"Error saving options: {e}")

def get_ollama_models():
    """Get list of installed Ollama models"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            # Parse the output to extract model names
            models = []
            for line in result.stdout.split('\n')[1:]:  # Skip header line
                if line.strip():
                    model_name = line.split()[0]  # First column is model name
                    models.append(model_name)
            return models
        return []
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

def load_available_models():
    """
    Load available models from both Ollama and OpenAI
    """
    models = {
        'ollama': get_ollama_models(),
        'openai': DEFAULT_AVAILABLE_MODELS.copy()
    }
    
    if os.path.exists(MODELS_FILE):
        try:
            with open(MODELS_FILE, 'r') as f:
                data = json.load(f)
                # Update OpenAI models if specified in models.json
                if 'available_models' in data:
                    models['openai'] = data['available_models']
        except json.JSONDecodeError as e:
            print(f"Error loading models: {e}")
    
    return models

def read_api_key():
    if ensure_sage_setup():
        key = load_key()
        try:
            with open(API_ENC_FILE, 'rb') as enc_file:
                encrypted_key = enc_file.read()
            return decrypt_api_key(encrypted_key, key)
        except Exception as e:
            print(f"Error reading encrypted API key: {e}")
            sys.exit(1)
    else:
        if os.path.exists(API_KEY_HELP_FILE):
            try:
                with open(API_KEY_HELP_FILE, 'r') as help_file:
                    help_text = help_file.read()
                    print(help_text)
            except Exception as e:
                print(f"Error reading help file: {e}")
                sys.exit(1)
        else:
            print("Help file not found. Please ensure 'Get_API_Key.txt' exists.")
            sys.exit(1)
        choice = input("API key not found. Would you like to enter your API key now? (y/n): ").strip().lower()
        if choice == 'y':
            api_key_input = input("Please paste your OpenAI API key: ").strip()
            if api_key_input:
                key = load_key()
                encrypt_api_key(api_key_input, key)
                print("API key saved securely.")
                return api_key_input
            else:
                print("No API key entered. Exiting.")
                sys.exit(1)
        else:
            print("Exiting without setting API key.")
            sys.exit(1)
