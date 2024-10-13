import os
import sys
import openai
import platform
import socket
import getpass
import psutil
import subprocess
import shlex
from commands import show_help, exit_program, options_menu, manage_api_key, clear_conversation
from pathlib import Path
from config import load_options, load_available_models, save_options, read_api_key
from conversation import load_conversation, save_conversation, clear_conversation
from capture_tool import start_capture
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.formatted_text import HTML
from utils import ensure_sage_setup, load_key, encrypt_api_key, decrypt_api_key, encode_image
from rich.panel import Panel
from rich.syntax import Syntax
import textwrap
import tempfile
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
import re

console = Console()

HOME_DIR = str(Path.home())
SAGE_DIR = os.path.join(HOME_DIR, '.sage')
SECRET_KEY_FILE = os.path.join(SAGE_DIR, 'secret.key')
API_ENC_FILE = os.path.join(SAGE_DIR, 'api.enc')
API_KEY_HELP_FILE = '/usr/share/sage/Get_API_Key.txt'

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

def load_system_prompt():
    system_prompt_file = '/usr/share/sage/system_prompt.txt'
    if os.path.exists(system_prompt_file):
        try:
            with open(system_prompt_file, 'r') as f:
                system_prompt = f.read().strip()
                return system_prompt
        except Exception as e:
            print(f"Error loading system prompt: {e}")
            return None
    else:
        system_prompt = input("System prompt not found. Please enter a system prompt:\n")
        try:
            with open(system_prompt_file, 'w') as f:
                f.write(system_prompt)
        except Exception as e:
            print(f"Error saving system prompt: {e}")
        return system_prompt

def gather_system_info():
    try:
        user_name = getpass.getuser()
        host_name = socket.gethostname()
        os_details = platform.platform()
        os_version = platform.version()
        processor = platform.processor()
        cpu_count = os.cpu_count()
        total_memory = psutil.virtual_memory().total // (1024 ** 2)
        uptime = subprocess.check_output(['uptime', '-p']).decode().strip()
        ip_address = socket.gethostbyname(host_name)

        try:
            installed_packages = subprocess.check_output(['dpkg', '--get-selections']).decode().strip()
        except Exception:
            installed_packages = "Could not retrieve installed packages."

        shell = os.environ.get('SHELL', 'Unknown')
        terminal = os.environ.get('TERM', 'Unknown')

        system_info = (
            f"User: {user_name}\n"
            f"Host: {host_name}\n"
            f"OS: {os_details} (Version: {os_version})\n"
            f"Processor: {processor}\n"
            f"CPU Count: {cpu_count}\n"
            f"Total Memory: {total_memory} MB\n"
            f"Uptime: {uptime}\n"
            f"IP Address: {ip_address}\n"
            f"Installed Packages: {installed_packages}\n"
            f"Shell: {shell}\n"
            f"Terminal: {terminal}"
        )
        return system_info
    except Exception as e:
        print(f"Error gathering system info: {e}")
        return "Failed to gather system information."

def capture_and_process(conversation, options):
    captured_image_path = start_capture()
    if os.path.exists(captured_image_path):
        console.print("[green]Image captured.[/green]")
        prompt = input("Enter your question about the captured image: ")
        
        # Encode the image
        base64_image = encode_image(captured_image_path)
        
        # Prepare the messages for the API
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        # Process with AI
        try:
            response = openai.ChatCompletion.create(
                model=options['model'],
                messages=messages,
                max_tokens=options['max_tokens']
            )
            assistant_message = response['choices'][0]['message']['content']
            
            # Convert markdown to Rich Markdown and display
            markdown = Markdown(assistant_message)
            console.print(Rule())
            console.print("[bold yellow]Assistant:[/bold yellow]")
            console.print(markdown)

            conversation.append({'role': 'user', 'content': f"[Image analysis request] {prompt}"})
            conversation.append({'role': 'assistant', 'content': assistant_message})
        except openai.error.OpenAIError as e:
            console.print(f"[red]An error occurred: {e}[/red]")
    else:
        print("Image capture failed or was cancelled.")

def summarize_conversation(conversation, options):
    summary_prompt = """Please summarize the following conversation by extracting key points about the user only. Organize the summary into these categories:

1. User Preferences: The user's likes, dislikes, and preferences.
2. Interests: Topics the user is interested in or passionate about.
3. Goals: Short-term and long-term objectives the user has attempted to achieve.
4. Personal Information: Relevant personal details the user has shared and their system information.

Gather as much information about the user and their system beyond that gathered at initiation. Remember their goals. 
Do not include any details about the AI assistant's capabilities, traits."""

    for message in conversation:
        if message['role'] != 'system':
            summary_prompt += f"\n{message['role'].capitalize()}: {message['content']}"
    
    try:
        summary_response = openai.ChatCompletion.create(
            model=options['model'],
            messages=[{'role': 'user', 'content': summary_prompt}],
            temperature=0.2,
            max_tokens=500
        )
        return summary_response['choices'][0]['message']['content']
    except openai.error.OpenAIError as e:
        console.print(f"[red]An error occurred while summarizing the conversation: {e}[/red]")
        return "Unable to generate summary due to an error."

def extract_bash_commands(text):
    """
    Extracts bash commands from the given text by finding all ```bash``` code blocks.
    
    Args:
        text (str): The text containing potential bash code blocks.
        
    Returns:
        List[str]: A list of bash commands extracted from the code blocks.
    """
    pattern = re.compile(r'```bash\s*\n(.*?)```', re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(text)
    
    commands = []
    for block in matches:
        for line in block.strip().split('\n'):
            line = line.strip()
            if line and not line.lower().startswith('bash'):
                commands.append(line)
    return commands

def execute_bash_command(command, options):
    """
    Executes a bash command in a new terminal window.
    The terminal will close automatically after the command completes.
    
    Args:
        command (str): The bash command to execute.
        options (Dict[str, Any]): Configuration options.
        
    Returns:
        None
    """
    terminal = options.get('terminal_emulator', 'gnome-terminal')
    
    if terminal == 'gnome-terminal':
        cmd = [terminal, '--', 'bash', '-c', f"{command}; echo 'Command completed. This window will close in 5 seconds.'; sleep 5"]
    elif terminal == 'xterm':
        cmd = [terminal, '-e', f"bash -c '{command}; echo \"Command completed. This window will close in 5 seconds.\"; sleep 5'"]
    elif terminal == 'konsole':
        cmd = [terminal, '-e', f"bash -c '{command}; echo \"Command completed. This window will close in 5 seconds.\"; sleep 5'"]
    elif terminal == 'xfce4-terminal':
        cmd = [terminal, '--command', f"bash -c '{command}; echo \"Command completed. This window will close in 5 seconds.\"; sleep 5'"]
    else:
        # Default fallback
        cmd = [terminal, '--', 'bash', '-c', f"{command}; echo 'Command completed. This window will close in 5 seconds.'; sleep 5"]
    
    try:
        subprocess.Popen(cmd)
        console.print(f"[bold green]Executing command in {terminal}: [/] {command}")
    except FileNotFoundError:
        console.print(f"[red]Terminal emulator '{terminal}' not found. Please install it or specify a different one in the configuration.[/red]")
    except Exception as e:
        console.print(f"[red]Failed to execute command '{command}' in terminal '{terminal}': {e}[/red]")

def handle_bash_commands(bash_commands, conversation, options):
    """
    Handles the execution of a list of bash commands by spawning new terminal windows.
    Allows users to cycle through commands, execute them independently, or return to the main prompt.
    
    Args:
        bash_commands (List[str]): Initial list of bash commands to execute.
        conversation (List[Dict[str, str]]): The conversation history.
        options (Dict[str, Any]): Configuration options.
    """
    if not bash_commands:
        return

    all_commands = bash_commands.copy()
    current_command_index = 0

    history = InMemoryHistory()
    for cmd in all_commands:
        history.append_string(cmd)

    kb = KeyBindings()

    @kb.add('enter')
    def _(event):
        event.current_buffer.validate_and_handle()

    @kb.add('up')
    def _(event):
        nonlocal current_command_index
        current_command_index = (current_command_index - 1) % len(all_commands)
        event.current_buffer.text = all_commands[current_command_index]

    @kb.add('down')
    def _(event):
        nonlocal current_command_index
        current_command_index = (current_command_index + 1) % len(all_commands)
        event.current_buffer.text = all_commands[current_command_index]

    session = PromptSession(
        history=history,
        key_bindings=kb,
        enable_history_search=False
    )

    console.print(f"\n[bold yellow]Bash command(s) detected. Use up/down arrows to cycle through commands, Enter to execute, or type 'exit' to return to the main prompt.[/bold yellow]")

    while True:
        try:
            user_input = session.prompt(
                HTML('<ansibrightcyan>Suggested Command (Enter to execute, "exit" to return): </ansibrightcyan>'),
                default=all_commands[current_command_index] if current_command_index < len(all_commands) else "",
                refresh_interval=0.5
            ).strip()

            if user_input.lower() == 'exit':
                console.print("[yellow]Returning to main prompt.[/yellow]")
                break

            if user_input.lower() == 'skip':
                console.print("[yellow]Command execution skipped.[/yellow]")
                current_command_index += 1
                if current_command_index >= len(all_commands):
                    current_command_index = 0
                continue

            if user_input:
                console.print(f"\n[bold green]Spawning terminal to execute command:[/bold green] {user_input}\n")
                execute_bash_command(user_input, options)

                conversation.append({'role': 'system', 'content': f"Command executed: {user_input} (output handled in separate terminal)"})

                current_command_index += 1
                if current_command_index >= len(all_commands):
                    current_command_index = 0

        except KeyboardInterrupt:
            console.print("\n[yellow]Command execution interrupted. Type 'exit' to return to main prompt or continue with another command.[/yellow]")
            continue
        except EOFError:
            console.print("\n[red]Unexpected end of input. Returning to main prompt.[/red]")
            break

    console.print("[bold green]Returning to main conversation prompt.[/bold green]")

def main():
    ensure_sage_setup()
    openai.api_key = read_api_key()
    options = load_options()
    conversation = load_conversation()
    system_prompt = load_system_prompt()

    if conversation and len(conversation) > 2:
        # Existing conversation found, generate summary
        summary = summarize_conversation(conversation, options)
        console.print(Panel(Markdown(summary), title="Previous Conversation Summary", border_style="cyan"))
        
        # Start fresh conversation with system prompt, new system info, and summary
        new_system_info = gather_system_info()
        conversation = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'system', 'content': new_system_info},
            {'role': 'system', 'content': f"Previous conversation summary: {summary}"}
        ]
        
        # Generate and display initial greeting
        greeting_query = (
            "Greet the user as Sage, a wise advisor for their system. Briefly mention your capabilities, "
            "their system information, and acknowledge the previous conversation summary. Then invite them to continue seeking your counsel."
        )
    else:
        # No existing conversation or it's too short, start fresh
        new_system_info = gather_system_info()
        conversation = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'system', 'content': new_system_info}
        ]
        
        # Generate and display initial greeting
        greeting_query = (
            "Greet the user as Sage, a wise advisor for their system. Briefly mention your capabilities and their system information then invite them to seek your counsel."
        )

    try:
        greeting_response = openai.ChatCompletion.create(
            model=options['model'],
            messages=conversation + [{'role': 'user', 'content': greeting_query}],
            temperature=1,
            max_tokens=options['max_tokens']
        )
        greeting_message = greeting_response['choices'][0]['message']['content']
        console.print(Rule())
        console.print("[bold green]Welcome to Sage, your wise system advisor:[/bold green]")
        console.print(Markdown(greeting_message))
        conversation.append({'role': 'assistant', 'content': greeting_message})
    except openai.error.OpenAIError as e:
        console.print(f"[red]An error occurred during initial greeting: {e}[/red]")

    available_models = load_available_models()
    if options['model'] not in available_models:
        console.print(f"[red]Current model '{options['model']}' is not in the list of available models.[/red]")
        options_menu(options)
        options = load_options()  # Reload options after menu
        if options['model'] not in available_models:
            console.print(f"[red]Selected model '{options['model']}' is still invalid. Exiting.[/red]")
            sys.exit(1)

    COMMANDS = {
        'help': show_help,
        'options': lambda: options_menu(options),
        'api': manage_api_key,
        'capture': lambda: capture_and_process(conversation, options),
        'clear': lambda: clear_conversation(),
        'exit': lambda: exit_program(conversation)
    }

    console.print(Rule())
    console.print("[bold green]How may I assist you today?[/bold green] (type 'exit' to quit or 'help' to show commands)")

    # Setup PromptSession without key bindings
    session = PromptSession()

    style = Style.from_dict({
        'prompt': 'bold cyan',
    })

    while True:
        try:
            # Prompt for user input (single-line)
            console.print(Rule())
            user_input = session.prompt(
                [('class:prompt', 'Prompt: ')],
                multiline=False,  # Single-line input
                style=style
            ).strip()  # Strip the input of leading/trailing whitespace

            # Check if input is empty
            if not user_input:
                continue  # Skip processing if input is empty

            if user_input.lower() in COMMANDS:
                if user_input.lower() == 'options':
                    options_menu(options)
                    # Reload options in case they were changed
                    options = load_options()
                elif user_input.lower() == 'clear':
                    conversation = COMMANDS[user_input.lower()]()
                    if not conversation:  # If conversation is empty after clearing
                        system_prompt = load_system_prompt()
                        system_info = gather_system_info()
                        conversation = [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'system', 'content': system_info}
                        ]
                else:
                    COMMANDS[user_input.lower()]()
                continue
            else:
                conversation.append({'role': 'user', 'content': user_input})

                # Add a rule (separator line) before the assistant's response
                console.print(Rule())

                # Handle context window size if applicable
                if options['context_window_size'] > 0:
                    context_size = options['context_window_size']
                    recent_conversation = conversation[2:]  # Start from index 2 to keep system info
                    num_messages_to_keep = context_size * 2  # user and assistant messages
                    if len(recent_conversation) > num_messages_to_keep:
                        conversation_trimmed = conversation[:2] + recent_conversation[-num_messages_to_keep:]
                        warning_message = (
                            f"[bold yellow]Warning:[/bold yellow] The conversation history exceeds the context window size. "
                            f"Only the most recent {num_messages_to_keep} messages (plus system messages) will be used for context."
                        )
                        console.print(Panel(warning_message, border_style="yellow"))
                    else:
                        conversation_trimmed = conversation
                else:
                    conversation_trimmed = conversation

                try:
                    response = openai.ChatCompletion.create(
                        model=options['model'],
                        messages=conversation_trimmed,
                        temperature=options['temperature'],
                        max_tokens=options['max_tokens']
                    )
                except openai.error.OpenAIError as e:
                    console.print(f"[red]An error occurred: {e}[/red]")
                    continue

                assistant_message = response['choices'][0]['message']['content']

                # Display the assistant's message
                console.print(Markdown(assistant_message))

                # Add assistant message to conversation
                conversation.append({'role': 'assistant', 'content': assistant_message})

                # Extract bash commands from the assistant's message
                bash_commands = extract_bash_commands(assistant_message)

                # Handle bash commands if any were detected
                if bash_commands:
                    handle_bash_commands(bash_commands, conversation, options)

        except EOFError:
            # Handle end of input (Ctrl+D) gracefully
            print("\nExiting program...")
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\nProgram interrupted. Exiting...")
            break

    exit_program(conversation)

if __name__ == "__main__":
    main()