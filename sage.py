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
import requests

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
    summary_prompt = """Please summarize the following conversation..."""
    
    try:
        if options['model_provider'] == 'ollama':
            summary_response = execute_ollama_request([{
                'role': 'user',
                'content': summary_prompt
            }], options)
            return summary_response
        else:
            summary_response = openai.ChatCompletion.create(
                model=options['model'],
                messages=[{'role': 'user', 'content': summary_prompt}],
                temperature=0.2,
                max_tokens=500
            )
            return summary_response['choices'][0]['message']['content']
    except Exception as e:
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
    except FileNotFoundError:
        console.print(f"[red]Terminal emulator '{terminal}' not found. Please install it or specify a different one in the configuration.[/red]")
    except Exception as e:
        console.print(f"[red]Failed to execute command '{command}' in terminal '{terminal}': {e}[/red]")

def handle_bash_commands(bash_commands, conversation, options, history):
    """
    Handles the execution of bash commands by adding them to history and executing them.
    
    Args:
        bash_commands (List[str]): List of bash commands to execute.
        conversation (List[Dict[str, str]]): The conversation history.
        options (Dict[str, Any]): Configuration options.
        history: The command history object.
    """
    if not bash_commands:
        return

    # Add commands to history
    for cmd in bash_commands:
        history.append_string(cmd)

    # Execute the commands
    for command in bash_commands:
        try:
            subprocess.Popen(cmd)
            console.print(f"[bold green]Executing command: [/] {command}")
            conversation.append({'role': 'system', 'content': f"Command executed: {command}"})
        except Exception as e:
            console.print(f"[red]Failed to execute command '{command}': {e}[/red]")

def is_valid_bash_command(command):
    """
    Check if a command is a valid bash command by using 'which'.
    
    Args:
        command (str): The command to check.
        
    Returns:
        bool: True if the command exists, False otherwise.
    """
    try:
        # Split the command to get just the executable part
        cmd_executable = shlex.split(command)[0]
        # Use 'which' to check if command exists in PATH
        result = subprocess.run(['which', cmd_executable], 
                              capture_output=True, 
                              text=True)
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, IndexError):
        return False

def execute_ollama_request(conversation, options):
    """Execute request to Ollama API"""
    messages = [msg for msg in conversation if msg['role'] != 'system']
    
    try:
        response = requests.post('http://localhost:11434/api/chat', json={
            'model': options['model'],
            'messages': messages,
            'stream': False
        })
        response.raise_for_status()
        return response.json()['message']['content']
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error communicating with Ollama: {e}[/red]")
        return None

def create_greeting(conversation, system_info, summary=None):
    """Create a personalized greeting based on known information"""
    
    # Get the system prompt from conversation
    system_prompt = next((msg['content'] for msg in conversation 
                         if msg['role'] == 'system' 
                         and msg['content'] != system_info 
                         and 'Previous conversation summary' not in msg['content']), None)
    
    # Parse system_info into structured data
    info_lines = system_info.split('\n')
    parsed_info = {}
    for line in info_lines:
        if ':' in line:
            key, value = line.split(':', 1)
            parsed_info[key.strip()] = value.strip()
    
    # Create a focused greeting query with specific instructions
    greeting_query = (
        f"Following this system prompt: '{system_prompt}'\n\n"
        f"As the digital sage and AI linux system administrator, craft a welcome message that includes:\n"
        f"1. An introduction of yourself as a linux system administrator. Use the user_name in the greeting.\n"
        f"2. A precise technical snapshot of the system using runtime system information: {system_info}\n"
        f"3. An short invitation to explore the technological abilities of this system, hinting at its latent computational superpowers\n\n"
    )
    
    # Extract previous context if available
    tech_details = next((msg['content'] for msg in conversation 
                        if msg['role'] == 'system' 
                        and 'Previous technical details:' in msg['content']), None)
    
    if tech_details:
        greeting_query += f"\nIncorporate relevant previous context: {tech_details}"
    
    if summary:
        greeting_query += f"\nPrevious conversation summary: {summary}"
    
    return greeting_query

def main():
    ensure_sage_setup()
    openai.api_key = read_api_key()
    options = load_options()
    
    # Load components in order
    system_prompt = load_system_prompt()
    system_info = gather_system_info()
    previous_conversation = load_conversation()

    # Initialize summary as None or an empty string
    summary = None
    
    # Initialize new conversation with system context
    conversation = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'system', 'content': system_info}
    ]    
    
    # If there's a previous conversation, summarize it
    if previous_conversation and len(previous_conversation) > 2:
        summary = summarize_conversation(previous_conversation, options)
        if summary:
            conversation.append({'role': 'system', 'content': f"Previous conversation summary: {summary}"})
            console.print(Panel(Markdown(summary), title="Previous Conversation Summary", border_style="cyan"))    
            
    # Create greeting that includes system info
    greeting_query = create_greeting(conversation, system_info, summary)

    try:
        if options['model_provider'] == 'ollama':
            greeting_message = execute_ollama_request([{
                'role': 'user',
                'content': greeting_query
            }], options)
        else:
            greeting_response = openai.ChatCompletion.create(
                model=options['model'],
                messages=conversation + [{'role': 'user', 'content': greeting_query}],
                temperature=0.7,
                max_tokens=options['max_tokens']
            )
            greeting_message = greeting_response['choices'][0]['message']['content']
        
        console.print(Rule())
        console.print(Markdown(greeting_message))
        conversation.append({'role': 'assistant', 'content': greeting_message})
    except Exception as e:
        console.print(f"[red]An error occurred during initial greeting: {e}[/red]")

    # Load the available models
    models = load_available_models()
    if options['model_provider'] == 'ollama':
        available_models = models.get('ollama', [])
    else:
        available_models = models.get('openai', [])

    if options['model'] not in available_models:
        console.print(f"[yellow]Warning: Current model '{options['model']}' is not in the list of available models.[/yellow]")
        # Set default model based on provider
        if options['model_provider'] == 'ollama':
            default_model = available_models[0] if available_models else 'llama2'
            console.print(f"[yellow]Using default model '{default_model}'[/yellow]")
            options['model'] = default_model
        else:
            default_model = available_models[0] if available_models else 'gpt-4o-mini'
            console.print(f"[yellow]Using default model '{default_model}'[/yellow]")
            options['model'] = default_model
        save_options(options)

    COMMANDS = {
        'help': show_help,
        'options': lambda: options_menu(options),
        'api': manage_api_key,
        'capture': lambda: capture_and_process(conversation, options),
        'clear': lambda: clear_conversation(),
        'exit': lambda: exit_program(conversation)
    }

    console.print("\n(type 'exit' to quit or 'help' to show commands)")

    # Setup unified history for commands and AI suggestions
    history = InMemoryHistory()
    
    # Setup PromptSession with history
    session = PromptSession(
        history=history,
        enable_history_search=True,
        auto_suggest=AutoSuggestFromHistory()
    )

    style = Style.from_dict({
        'prompt': 'bold cyan',
    })

    while True:
        try:
            # Prompt for user input with history support
            console.print(Rule())
            user_input = session.prompt(
                [('class:prompt', 'Prompt: ')],
                style=style
            ).strip()

            # Check if input is empty
            if not user_input:
                continue

            # First check for built-in commands
            if user_input.lower() in COMMANDS:
                if user_input.lower() == 'options':
                    options_menu(options)
                    options = load_options()
                elif user_input.lower() == 'clear':
                    conversation = COMMANDS[user_input.lower()]()
                    if not conversation:
                        system_prompt = load_system_prompt()
                        system_info = gather_system_info()
                        conversation = [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'system', 'content': system_info}
                        ]
                else:
                    COMMANDS[user_input.lower()]()
                continue

            # Then check if input is a valid bash command
            if is_valid_bash_command(user_input):
                execute_bash_command(user_input, options)
                conversation.append({'role': 'system', 'content': f"Command executed: {user_input}"})
                continue

            # If not a command, process with AI
            try:
                conversation.append({'role': 'user', 'content': user_input})
                
                if options['model_provider'] == 'ollama':
                    assistant_message = execute_ollama_request(conversation, options)
                    if assistant_message is None:
                        continue
                else:
                    response = openai.ChatCompletion.create(
                        model=options['model'],
                        messages=conversation,
                        temperature=options['temperature'],
                        max_tokens=options['max_tokens']
                    )
                    assistant_message = response['choices'][0]['message']['content']
                
                # Display the response
                console.print(Rule())
                console.print("[bold yellow]Sage:[/bold yellow]")
                console.print(Markdown(assistant_message))
                
                # Add response to conversation history
                conversation.append({'role': 'assistant', 'content': assistant_message})
                
                # Extract and add any bash commands from the response to history
                bash_commands = extract_bash_commands(assistant_message)
                for cmd in bash_commands:
                    history.append_string(cmd)
                    
            except openai.error.OpenAIError as e:
                console.print(f"[red]An error occurred: {e}[/red]")

        except EOFError:
            print("\nExiting program...")
            break
        except KeyboardInterrupt:
            print("\nProgram interrupted. Exiting...")
            break

    exit_program(conversation)

if __name__ == "__main__":
    main()