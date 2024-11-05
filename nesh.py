#!/usr/bin/env python3
import os
import json
import readline
import subprocess
import difflib
import shlex
import sys
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table  # 修正: Tableをrich.markdownではなくrich.tableからインポート

console = Console()
CONFIG_RC = os.path.expanduser("~/.neshrc")
CONFIG_COMMANDS = os.path.expanduser("~/.nesh/commands.json")
CONFIG_MESSAGES = os.path.expanduser("~/.nesh/messages.json")

class NeshScriptParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.aliases = {}
        self.language = "ENGLISH"  # Default language

    def parse_line(self, line, shell):
        line = line.strip()
        if not line or line.startswith("#"):
            return  # Ignore comments and empty lines

        tokens = shlex.split(line)
        if not tokens:
            return

        command = tokens[0].upper()

        if command == "CREATE":
            if len(tokens) < 3:
                shell.print_message("script_parse_error", error="Incomplete CREATE command", line=line)
                return
            sub_command = tokens[1].upper()
            if sub_command == "DIR":
                try:
                    path = self._extract_quoted_string(line)
                    self.create_dir(path, shell)
                except ValueError as e:
                    shell.print_message("script_parse_error", error=str(e), line=line)
            elif sub_command == "VAR":
                var_name, value = self.create_var(line, shell)
                if var_name and value is not None:
                    shell.environment[var_name] = value
            elif sub_command == "ALIAS":
                alias_name, alias_cmd = self.create_alias(line, shell)
                if alias_name and alias_cmd:
                    shell.aliases[alias_name] = alias_cmd
            elif sub_command == "CMD":
                from_index = line.upper().find('FROM')
                if from_index == -1:
                    shell.print_message("script_parse_error", error="Missing FROM keyword", line=line)
                    return
                try:
                    path = self._extract_quoted_string(line[from_index:])
                    shell.load_external_commands(path)
                except ValueError as e:
                    shell.print_message("script_parse_error", error=str(e), line=line)
            else:
                shell.print_message("create_command_error", sub_command=sub_command)
        elif command == "APPEND":
            self.append_to_var(line, shell)
        elif command == "SET":
            if len(tokens) < 3:
                shell.print_message("script_parse_error", error="Incomplete SET command", line=line)
                return
            sub_command = tokens[1].upper()
            if sub_command == "LANGUAGE":
                try:
                    language = self._extract_quoted_string(line)
                    shell.set_language(language)
                except ValueError as e:
                    shell.print_message("script_parse_error", error=str(e), line=line)
            elif sub_command == "VAR":
                self.set_var(line, shell)
            else:
                shell.print_message("unknown_command", command=command)
        elif command == "RUN":
            if len(tokens) < 3:
                shell.print_message("script_parse_error", error="Incomplete RUN command", line=line)
                return
            sub_command = tokens[1].upper()
            if sub_command == "CMD":
                try:
                    cmd = self._extract_quoted_string(line)
                    self.run_cmd(cmd, shell)
                except ValueError as e:
                    shell.print_message("script_parse_error", error=str(e), line=line)
            elif sub_command == "NESH":
                from_index = line.upper().find('FROM')
                if from_index == -1:
                    shell.print_message("script_parse_error", error="Missing FROM keyword", line=line)
                    return
                try:
                    path = self._extract_quoted_string(line[from_index:])
                    self.run_nesh_from_file(path, shell)
                except ValueError as e:
                    shell.print_message("script_parse_error", error=str(e), line=line)
            else:
                shell.print_message("unknown_command", command=command)
        elif command == "SAVE":
            self.save_preview_result(line, shell)
        elif command == "EXIT":
            shell.print_message("exit_message")
            shell.exit_shell()
        elif command == "SLEEP":
            self.sleep_command(line, shell)
        elif command == "REFLESH":
            shell.load_rc()
            shell.print_message("config_refreshed")
        elif command == "HELP":
            self.display_help(shell)
        else:
            shell.print_message("unknown_command", command=command)

    def execute(self, shell):
        if not os.path.exists(self.filepath):
            shell.print_message("script_not_found", path=self.filepath)
            return
        with open(self.filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    self.parse_line(line, shell)
                except Exception as e:
                    shell.print_message("script_parse_error", error=str(e), line=line.strip())

    def expand_variables(self, text, shell):
        # Expand variables in the format $VAR_NAME or ${VAR_NAME}
        for key, value in shell.environment.items():
            text = text.replace(f"${{{key}}}", str(value))
            text = text.replace(f"${key}", str(value))
        return text

    def _extract_quoted_string(self, text):
        first_quote = text.find('"')
        last_quote = text.rfind('"')
        if first_quote == -1 or last_quote == -1 or last_quote <= first_quote:
            raise ValueError(f"Invalid quoted string: {text}")
        return text[first_quote+1:last_quote]

    def create_dir(self, path, shell):
        path = os.path.expanduser(path)
        try:
            os.makedirs(path, exist_ok=True)
            shell.print_message("directory_created", path=path)
        except Exception as e:
            shell.print_message("command_execution_error", error=e)

    def create_var(self, line, shell):
        try:
            parts = shlex.split(line)
            var_index = parts.index("VAR") + 1
            with_index = parts.index("WITH") + 1
            var_type = parts[with_index].upper()
            value_part = line.split("WITH")[1].strip()
            
            var_name = parts[var_index].strip('$')
            
            if var_type == "TEXT":
                raw_value = self._extract_quoted_string(line)
                value = self.expand_variables(raw_value, shell)  # Expand variables in the value
            elif var_type == "BOOL":
                value_str = parts[with_index + 1].upper()
                if value_str not in ["TRUE", "FALSE"]:
                    shell.print_message("script_parse_error", error=f"Invalid BOOL value: {value_str}", line=line)
                    return var_name, None
                value = True if value_str == "TRUE" else False
            elif var_type == "OPTION":
                value = parts[with_index + 1].upper()
            else:
                shell.print_message("script_parse_error", error=f"Unsupported VAR type: {var_type}", line=line)
                return var_name, None

            shell.print_message("variable_set", var=f"${var_name}", value=value)
            return var_name, value
        except (ValueError, IndexError) as e:
            shell.print_message("script_parse_error", error=str(e), line=line)
            return None, None

    def create_alias(self, line, shell):
        try:
            parts = shlex.split(line)
            alias_index = parts.index("ALIAS") + 1
            for_index = parts.index("FOR") + 1

            alias_name = parts[alias_index]
            alias_cmd = self._extract_quoted_string(line[line.upper().find('FOR'):])
            shell.print_message("alias_created", alias=alias_name, command=alias_cmd)
            return alias_name, alias_cmd
        except Exception as e:
            shell.print_message("script_parse_error", error=str(e), line=line)
            return None, None

    def append_to_var(self, line, shell):
        try:
            parts = shlex.split(line)
            to_index = parts.index("TO") + 1

            # Extract the value to append and expand variables within it
            raw_value = self._extract_quoted_string(line)
            value = self.expand_variables(raw_value, shell)  # Expand variables in the value
            var_name = parts[to_index].strip('$')

            # Get the current value and ensure it's a string
            current = shell.environment.get(var_name, "")
            if isinstance(current, bool):
                shell.print_message("script_parse_error", error=f"Cannot append to boolean variable: {var_name}", line=line)
                return

            # Only append if value is not already in PATH
            if value not in current.split(':'):
                new_value = f"{current}:{value}" if current else value
                shell.environment[var_name] = new_value
                shell.print_message("variable_set", var=f"${var_name}", value=new_value)
        except Exception as e:
            shell.print_message("script_parse_error", error=str(e), line=line)

    def set_var(self, line, shell):
        try:
            parts = shlex.split(line)
            var_index = parts.index("VAR") + 1
            with_index = parts.index("WITH") + 1
            type_or_option = parts[with_index].upper()
            value = parts[with_index + 1].upper()

            var_name = parts[var_index].strip('$')

            if type_or_option == "BOOL":
                if value not in ["TRUE", "FALSE"]:
                    shell.print_message("script_parse_error", error=f"Invalid BOOL value: {value}", line=line)
                    return
                var_value = True if value == "TRUE" else False
            elif type_or_option == "OPTION":
                var_value = value
            else:
                shell.print_message("script_parse_error", error=f"Unsupported SET VAR type: {type_or_option}", line=line)
                return

            shell.environment[var_name] = var_value
            shell.print_message("variable_set", var=f"${var_name}", value=var_value)
        except Exception as e:
            shell.print_message("script_parse_error", error=str(e), line=line)

    def run_cmd(self, cmd, shell):
        cmd = self.expand_variables(cmd, shell)  # Expand variables in the command
        shell.print_message("run_cmd_executed", cmd=cmd)
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=shell.get_environment())
            shell.last_command_result = result.stdout.strip()
            if result.stdout:
                print(result.stdout, end='')  # Print the command's output
            if result.stderr:
                print(result.stderr, end='')
        except Exception as e:
            shell.print_message("command_execution_error", error=e)

    def run_nesh_from_file(self, path, shell):
        shell.print_message("run_nesh_executed", path=path)
        parser = NeshScriptParser(os.path.expanduser(path))
        parser.language = shell.language
        parser.execute(shell)  # Ensure execute method is called

    def save_preview_result(self, line, shell):
        try:
            parts = shlex.split(line)
            to_index = parts.index("TO") + 1
            path = self._extract_quoted_string(line)
            if hasattr(shell, 'last_command_result') and shell.last_command_result:
                with open(os.path.expanduser(path), 'w', encoding='utf-8') as f:
                    f.write(shell.last_command_result)
                shell.print_message("save_preview_result", path=path)
            else:
                shell.print_message("script_parse_error", error="No command result to save.", line=line)
        except Exception as e:
            shell.print_message("script_parse_error", error=str(e), line=line)

    def sleep_command(self, line, shell):
        try:
            parts = shlex.split(line)
            with_index = parts.index("WITH") + 1
            if parts[with_index].upper() == "SECOND":
                seconds = int(parts[with_index + 1])
                shell.print_message("sleep_executed", seconds=seconds)
                time.sleep(seconds)
            else:
                shell.print_message("script_parse_error", error="Unsupported SLEEP option.", line=line)
        except Exception as e:
            shell.print_message("script_parse_error", error=str(e), line=line)

    def display_help(self, shell):
        table = Table(title="Nesh Help")

        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Subcommand", style="magenta")
        table.add_column("Parameters", style="green")
        table.add_column("Description", style="yellow", width=77)

        table.add_row("CREATE", "DIR", '"<directory_path>"', "Creates a directory at the specified path.")
        table.add_row("CREATE", "VAR", "$VAR_NAME WITH TYPE VALUE", "Creates a variable with a specific type (`TEXT`, `BOOL`, `OPTION`) and value.")
        table.add_row("CREATE", "ALIAS", 'ALIAS FOR "<command>"', "Creates an alias that maps to a specified command.")
        table.add_row("CREATE", "CMD", 'FROM "<path>"', "Loads commands from an external file at the given path.")
        table.add_row("APPEND", "", '"<value>" TO $VAR_NAME', "Appends a value to an existing variable.")
        table.add_row("SET", "LANGUAGE", '"<language>"', 'Sets the language of the shell (options: `"ENGLISH"`, `"日本語"`).')
        table.add_row("SET", "VAR", "$VAR_NAME WITH TYPE VALUE", "Sets an existing variable’s value with specific type (`BOOL`, `OPTION`).")
        table.add_row("RUN", "CMD", '"<command>"', "Runs a specified command and captures its output.")
        table.add_row("RUN", "NESH", 'FROM "<file_path>"', "Runs commands from a specified Nesh script file.")
        table.add_row("SAVE", "", '"<output_file>"', "Saves the last command result to a specified file path.")
        table.add_row("EXIT", "", "", "Exits the shell.")
        table.add_row("SLEEP", "", 'WITH SECOND <seconds>', "Pauses execution for a specified number of seconds.")
        table.add_row("REFLESH", "", "", "Reloads the configuration from `~/.neshrc`.")

        console.print(table)

    def execute(self, shell):
        if not os.path.exists(self.filepath):
            shell.print_message("script_not_found", path=self.filepath)
            return
        with open(self.filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    self.parse_line(line, shell)
                except Exception as e:
                    shell.print_message("script_parse_error", error=str(e), line=line.strip())

class Nesh:
    def __init__(self):
        self.commands = {}
        self.aliases = {}
        self.environment = os.environ.copy()  # Initialize with system environment
        self.language = "ENGLISH"
        self.last_command_result = ""
        self.messages = self.load_messages()
        self.load_commands()
        self.load_rc()

    def load_messages(self):
        messages_path = CONFIG_MESSAGES
        if os.path.exists(messages_path):
            try:
                with open(messages_path, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                    return messages
            except json.JSONDecodeError as e:
                print(f"メッセージファイルの解析エラー: {e}")
                sys.exit(1)
        else:
            print(f"メッセージファイルが見つかりません: {messages_path}")
            sys.exit(1)

    def load_rc(self):
        parser = NeshScriptParser(CONFIG_RC)
        parser.execute(self)

    def set_language(self, language):
        language_upper = language.upper()
        if language_upper in ["ENGLISH", "日本語"]:
            self.language = language_upper
        elif language.lower() == "japanese":
            self.language = "日本語"
        elif language.lower() == "english":
            self.language = "ENGLISH"
        else:
            self.print_message("unsupported_language", language=language)
            self.language = "ENGLISH"

    def print_message(self, message_key, **kwargs):
        message_template = self.messages.get(message_key, {}).get(self.language, "")
        if message_template:
            console.print(Markdown(message_template.format(**kwargs)))
        else:
            fallback = self.messages.get(message_key, {}).get("ENGLISH", "")
            console.print(Markdown(fallback.format(**kwargs)))

    def load_commands(self):
        if os.path.exists(CONFIG_COMMANDS):
            try:
                with open(CONFIG_COMMANDS, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.commands = data.get("commands", {})
            except json.JSONDecodeError as e:
                self.print_message("script_parse_error", error=e, line="Loading commands.json")
                sys.exit(1)
        else:
            self.print_message("script_not_found", path=CONFIG_COMMANDS)
            sys.exit(1)

    def load_external_commands(self, path):
        path = os.path.expanduser(path)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    external_commands = data.get("commands", {})
                    self.commands.update(external_commands)
                    self.print_message("external_commands_loaded", path=path)
            except json.JSONDecodeError as e:
                self.print_message("script_parse_error", error=e, line=path)
        else:
            self.print_message("script_not_found", path=path)

    def get_environment(self):
        env = os.environ.copy()  # Start with a copy of the system environment

        # Update PATH explicitly if it's been modified
        if "PATH" in self.environment:
            env["PATH"] = self.environment["PATH"]

        # Add other environment variables (excluding PATH)
        for key, value in self.environment.items():
            if key != "PATH":
                env[key] = str(value)

        return env

    def completer(self, text, state):
        buffer = readline.get_line_buffer()
        try:
            tokens = shlex.split(buffer)
        except ValueError:
            tokens = buffer.split()

        if not tokens:
            options = list(self.commands.keys()) + list(self.aliases.keys()) + ["CREATE", "APPEND", "SET", "RUN", "SAVE", "EXIT", "SLEEP", "REFLESH", "HELP"]
        elif len(tokens) == 1:
            options = [cmd for cmd in list(self.commands.keys()) + list(self.aliases.keys()) + ["CREATE", "APPEND", "SET", "RUN", "SAVE", "EXIT", "SLEEP", "REFLESH", "HELP"] if cmd.startswith(text.upper())]
        else:
            cmd = tokens[0].upper()
            if cmd in self.commands:
                args = self.commands.get(cmd, {}).get("arguments", [])
                options = [arg for arg in args if arg.startswith(text)]
            else:
                options = []
        try:
            return options[state]
        except IndexError:
            return None

    def spell_check(self, cmd):
        possible = difflib.get_close_matches(cmd.upper(), list(self.commands.keys()) + list(self.aliases.keys()) + ["CREATE", "APPEND", "SET", "RUN", "SAVE", "EXIT", "SLEEP", "REFLESH", "HELP"], n=1, cutoff=0.6)
        if possible:
            return possible[0]
        return None

    def run_command(self, cmd_line):
        if not cmd_line.strip():
            return

        # Split the command line into tokens and get the first token as the command
        tokens = shlex.split(cmd_line)
        if not tokens:
            return
        first_word = tokens[0].upper()

        # Check if the first word is an alias
        if first_word in self.aliases:
            # Replace the command line with the expanded alias
            alias_expansion = self.aliases[first_word]
            # Replace the alias with its command
            new_cmd_line = alias_expansion + ' ' + ' '.join(tokens[1:])
            self.run_command(new_cmd_line)  # Recursive call with expanded command
            return

        nesh_commands = ["CREATE", "APPEND", "SET", "RUN", "SAVE", "EXIT", "SLEEP", "REFLESH", "HELP"]

        if first_word in nesh_commands:
            parser = NeshScriptParser("")
            parser.filepath = ""
            try:
                parser.parse_line(cmd_line, self)
            except Exception as e:
                self.print_message("script_parse_error", error=str(e), line=cmd_line)
        else:
            try:
                env = self.get_environment()
                result = subprocess.run(cmd_line, shell=True, capture_output=True, text=True, env=env)
                self.last_command_result = result.stdout.strip()
                if result.stdout and not self.environment.get("NESHRC_RESULT_HIDE", False):
                    print(result.stdout, end='')  # Print the command's output
                if result.stderr:
                    print(result.stderr, end='')
            except Exception as e:
                self.print_message("command_execution_error", error=e)

    def exit_shell(self):
        sys.exit(0)

    def start(self):
        readline.set_completer(self.completer)
        readline.parse_and_bind("tab: complete")
        while True:
            try:
                prompt = self.messages["prompt"].get(self.language, "nesh> ")
                if self.environment.get("NESH_PWD_SHOW") == "IN_PROMPT":
                    pwd = os.getcwd()
                    prompt = f"{pwd} {prompt}"
                cmd_line = input(prompt)
                if cmd_line.strip().lower() in ['exit', 'quit']:
                    self.print_message("exit_message")
                    break
                self.run_command(cmd_line)
            except (EOFError, KeyboardInterrupt):
                self.print_message("exit_message")
                break

if __name__ == "__main__":
    shell = Nesh()
    shell.start()
