# Nesh
A new shell that can run regular commands (/bin/sh) as well as Nesh Scripts.

## Nesh Script

| Command      | Subcommand         | Parameters                  | Description                                                                                       |
|--------------|--------------------|-----------------------------|---------------------------------------------------------------------------------------------------|
| **CREATE**   | `DIR`              | `"<directory_path>"`        | Creates a directory at the specified path.                                                       |
|              | `VAR`              | `$VAR_NAME WITH TYPE VALUE` | Creates a variable with a specific type (`TEXT`, `BOOL`, `OPTION`) and value.                     |
|              | `ALIAS`            | `ALIAS FOR "<command>"`     | Creates an alias that maps to a specified command.                                               |
|              | `CMD`              | `FROM "<path>"`             | Loads commands from an external file at the given path.                                          |
| **APPEND**   |                    | `"<value>" TO $VAR_NAME`    | Appends a value to an existing variable.                                                         |
| **SET**      | `LANGUAGE`         | `"<language>"`              | Sets the language of the shell (options: `"ENGLISH"`, `"日本語"`).                                |
|              | `VAR`              | `$VAR_NAME WITH TYPE VALUE` | Sets an existing variable’s value with specific type (`BOOL`, `OPTION`).                          |
| **RUN**      | `CMD`              | `"<command>"`               | Runs a specified command and captures its output.                                                |
|              | `NESH`             | `FROM "<file_path>"`        | Runs commands from a specified Nesh script file.                                                 |
| **SAVE**     |                    | `"<output_file>"`           | Saves the last command result to a specified file path.                                          |
| **EXIT**     |                    |                             | Exits the shell.                                                                                  |
| **SLEEP**    |                    | `WITH SECOND <seconds>`     | Pauses execution for a specified number of seconds.                                              |
| **REFLESH**  |                    |                             | Reloads the configuration from `~/.neshrc`.                                                      |

## Locations
- `nesh.py`: Any Location is Supported
- `commands.json`: `~/.nesh/commands.json`
- `messages.json`: `~/.nesh/messages.json`
