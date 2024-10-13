# commands.py

import sys
import os
from config import save_options, load_available_models, read_api_key 
from utils import encrypt_api_key, load_key
from conversation import clear_conversation, save_conversation
from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "danger": "bold red",
    "success": "bold green"
})

console = Console(theme=custom_theme)

def show_help():
    help_text = """
Available commands:
- help: Show this help message
- options: Configure application settings
- api: Manage API key
- capture: Capture screen and send image to AI
- clear: Clear the conversation history
- exit: Exit the program
    """
    print(help_text)


def exit_program(conversation):
    save_conversation(conversation)
    console.print("[success]Conversation has been summarized and saved. Goodbye![/success]")
    sys.exit(0)


def manage_api_key():
    API_ENC_FILE = os.path.join(os.path.expanduser('~'), '.sage', 'api.enc')
    while True:
        choice = input("API Key Management:\n1. View current API key (masked)\n2. Replace API key\n3. Remove API key\n4. Back to main menu\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            current_key = read_api_key()
            if current_key:
                masked_key = f"{current_key[:5]}...{current_key[-5:]}"
                print(f"Current API key: {masked_key}")
            else:
                print("No API key is currently set.")
        elif choice == '2':
            new_key = input("Enter new API key: ").strip()
            if new_key:
                key = load_key()
                encrypt_api_key(new_key, key)
                print("API key updated successfully.")
            else:
                print("No key entered. Operation cancelled.")
        elif choice == '3':
            confirm = input("Are you sure you want to remove the API key? (y/n): ").strip().lower()
            if confirm == 'y':
                try:
                    os.remove(API_ENC_FILE)
                    print("API key removed successfully.")
                except FileNotFoundError:
                    print("No API key file found.")
                except Exception as e:
                    print(f"Error removing API key: {e}")
            else:
                print("Operation cancelled.")
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")


def options_menu(options):
    original_options = options.copy()
    available_models = load_available_models()

    while True:
        console.print("\n[bold]Options Menu:[/bold]")
        console.print(f"1. Model: [cyan]{options['model']}[/cyan]")
        console.print(f"2. Temperature: [cyan]{options['temperature']}[/cyan]")
        console.print(f"3. Max tokens: [cyan]{options['max_tokens']}[/cyan]")
        console.print(f"4. Context window size: [cyan]{options['context_window_size']}[/cyan]")
        console.print("5. Save changes and return")
        console.print("6. Cancel changes and return")
        
        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == '1':
            console.print("\nAvailable models:")
            for i, model in enumerate(available_models, 1):
                console.print(f"{i}. {model}")
            model_choice = input("Enter the number of the model you want to use: ").strip()
            try:
                model_index = int(model_choice) - 1
                if 0 <= model_index < len(available_models):
                    options['model'] = available_models[model_index]
                else:
                    console.print("[warning]Invalid model number. No changes made.[/warning]")
            except ValueError:
                console.print("[warning]Invalid input. No changes made.[/warning]")
        elif choice == '2':
            new_temp = input("Enter new temperature (0.0 - 1.0): ").strip()
            try:
                new_temp = float(new_temp)
                if 0.0 <= new_temp <= 1.0:
                    options['temperature'] = new_temp
                else:
                    console.print("[warning]Temperature must be between 0.0 and 1.0. No changes made.[/warning]")
            except ValueError:
                console.print("[warning]Invalid temperature value. No changes made.[/warning]")
        elif choice == '3':
            new_max_tokens = input("Enter new max tokens: ").strip()
            try:
                new_max_tokens = int(new_max_tokens)
                if new_max_tokens > 0:
                    options['max_tokens'] = new_max_tokens
                else:
                    console.print("[warning]Max tokens must be greater than 0. No changes made.[/warning]")
            except ValueError:
                console.print("[warning]Invalid max tokens value. No changes made.[/warning]")
        elif choice == '4':
            new_context_size = input("Enter new context window size: ").strip()
            try:
                new_context_size = int(new_context_size)
                if new_context_size >= 0:
                    options['context_window_size'] = new_context_size
                else:
                    console.print("[warning]Context window size must be 0 or greater. No changes made.[/warning]")
            except ValueError:
                console.print("[warning]Invalid context window size value. No changes made.[/warning]")
        elif choice == '5':
            save_options(options)
            console.print("[success]Options saved. Returning to main menu.[/success]")
            return
        elif choice == '6':
            console.print("[info]Changes canceled. Returning to main menu.[/info]")
            return original_options
        else:
            console.print("[warning]Invalid choice. Please try again.[/warning]")
