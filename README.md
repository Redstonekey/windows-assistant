# Windows Quick Assistant

## Overview
The Windows Quick Assistant is a Python-based tool that provides a user-friendly interface for managing and executing commands using hotkeys, voice recognition, and a simple text input field. It is built using PyQt5 and integrates SQLite for database management.

## Features

1. **Quick Action Window**:
   - Frameless and always-on-top window.
   - Allows users to type commands or use voice recognition.
   - Executes predefined actions based on user input.

2. **Voice Recognition**:
   - Supports both German and English.
   - Converts spoken numbers into digits.

3. **Database Management**:
   - Add, delete, and view commands stored in an SQLite database.
   - Commands are categorized by prefix, value, and executable command.

4. **Hotkey Integration**:
   - Opens the Quick Action Window using the `Alt + Space` hotkey.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python quick_action.py
   ```

2. Use `Alt + Space` to open the Quick Action Window.
3. Type or speak commands to execute predefined actions.
4. Use "11" as input to open the Database Management Window and manage commands.

## File Structure

- `quick_action.py`: Main application file.
- `actions.db`: SQLite database file for storing commands.
- `requirements.txt`: Contains the list of dependencies.
- `README.md`: Documentation for the application.

## Dependencies

- PyQt5
- keyboard
- speech_recognition
- sqlite3

## Notes

- Ensure your microphone is set up correctly for voice recognition.
- The application supports both German and English for voice commands.
- Commands can be added, deleted, and managed via the Database Management Window.

## License

This project is licensed under the MIT License.