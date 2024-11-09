# conversation.py

import json
import os
from pathlib import Path

HOME_DIR = str(Path.home())
SAGE_DIR = os.path.join(HOME_DIR, '.sage')
CONVERSATION_FILE = os.path.join(SAGE_DIR, 'conversation.json')

def load_conversation():
    """Load the previous conversation summary"""
    if os.path.exists(CONVERSATION_FILE):
        try:
            with open(CONVERSATION_FILE, 'r') as f:
                summary = json.load(f)
            
            # Convert summary back into conversation format
            conversation = []
            
            # Check if summary is a dictionary (expected format)
            if isinstance(summary, dict) and (summary.get('key_points') or summary.get('topics_discussed')):
                conversation.append({
                    'role': 'system',
                    'content': (
                        "Previous conversation summary:\n"
                        f"Topics discussed: {', '.join(summary['topics_discussed'])}\n"
                        f"Key points: {', '.join(summary['key_points'])}"
                    )
                })
                
            return conversation
        except json.JSONDecodeError as e:
            print(f"Error loading conversation summary: {e}")
            return []
    return []

def save_conversation(conversation):
    """Summarize and save the important details from the conversation"""
    try:
        summary = {
            'key_points': [],
            'topics_discussed': [],
            'user_preferences': {}
        }
        
        # Analyze conversation for important points and topics
        for msg in conversation:
            if msg['role'] == 'user':
                # Add user queries to topics discussed
                summary['topics_discussed'].append(msg['content'])
            elif msg['role'] == 'assistant':
                # Extract key points from assistant responses
                if len(msg['content']) > 50:  # Only summarize substantial responses
                    summary['key_points'].append(msg['content'][:100] + "...")  # Store beginning of response
        
        # Keep only the most recent topics and points
        summary['topics_discussed'] = summary['topics_discussed'][-5:]  # Keep last 5 topics
        summary['key_points'] = summary['key_points'][-3:]  # Keep last 3 key points
        
        # Save the summarized conversation
        os.makedirs(SAGE_DIR, exist_ok=True)
        with open(CONVERSATION_FILE, 'w') as f:
            json.dump(summary, f, indent=4)
            
    except Exception as e:
        print(f"Error saving conversation summary: {e}")

def clear_conversation():
    if os.path.exists(CONVERSATION_FILE):
        os.remove(CONVERSATION_FILE)
    print("Conversation cleared.")
    return []
