# conversation.py

import json
import os
from pathlib import Path

HOME_DIR = str(Path.home())
SAGE_DIR = os.path.join(HOME_DIR, '.sage')
CONVERSATION_FILE = os.path.join(SAGE_DIR, 'conversation.json')

def load_conversation():
    if os.path.exists(CONVERSATION_FILE):
        try:
            with open(CONVERSATION_FILE, 'r') as f:
                conversation = json.load(f)
                return conversation
        except json.JSONDecodeError as e:
            print(f"Error loading conversation: {e}")
            return []
    else:
        return []

def save_conversation(conversation):
    try:
        os.makedirs(SAGE_DIR, exist_ok=True)
        with open(CONVERSATION_FILE, 'w') as f:
            json.dump(conversation, f, indent=4)
    except Exception as e:
        print(f"Error saving conversation: {e}")

def clear_conversation():
    if os.path.exists(CONVERSATION_FILE):
        os.remove(CONVERSATION_FILE)
    print("Conversation cleared.")
    return []
