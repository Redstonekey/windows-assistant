import sys
import threading
from PyQt5 import QtWidgets, QtCore, QtGui
import keyboard
import speech_recognition as sr
import sqlite3
import subprocess

class DatabaseManagementWindow(QtWidgets.QWidget):
    def __init__(self, db_cursor):
        super().__init__()
        self.setWindowTitle("Manage Commands")
        self.setFixedSize(600, 400)
        self.db_cursor = db_cursor

        layout = QtWidgets.QVBoxLayout(self)

        self.command_list = QtWidgets.QListWidget(self)
        self.load_commands()
        layout.addWidget(self.command_list)

        self.add_button = QtWidgets.QPushButton("Add Command", self)
        self.add_button.clicked.connect(self.add_command)
        layout.addWidget(self.add_button)

        self.delete_button = QtWidgets.QPushButton("Delete Command", self)
        self.delete_button.clicked.connect(self.delete_command)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def load_commands(self):
        self.command_list.clear()
        self.db_cursor.execute("SELECT prefix, value, command, open_window FROM actions")
        for prefix, value, command, open_window in self.db_cursor.fetchall():
            run_mode = 'Yes' if open_window else 'No'
            self.command_list.addItem(f"Prefix: {prefix}, Value: {value}, Command: {command}, Window: {run_mode}")

    def add_command(self):
        prefix, ok_prefix = QtWidgets.QInputDialog.getText(self, "Add Command", "Enter prefix:")
        if not ok_prefix or not prefix:
            return

        value, ok_value = QtWidgets.QInputDialog.getText(self, "Add Command", "Enter value (optional):")
        if not ok_value:
            value = ""

        command, ok_command = QtWidgets.QInputDialog.getText(self, "Add Command", "Enter command:")
        if not ok_command or not command:
            return

        # Ask whether to open a cmd window or run quietly
        choice, ok_choice = QtWidgets.QInputDialog.getItem(self, "Add Command", "Run mode:", ["Open window", "Run quietly"], 0, False)
        if not ok_choice:
            open_window = 1
        else:
            open_window = 1 if choice == "Open window" else 0

        self.db_cursor.execute("INSERT INTO actions (prefix, value, command, open_window) VALUES (?, ?, ?, ?)", (prefix, value, command, open_window))
        self.db_cursor.connection.commit()
        self.load_commands()

    def delete_command(self):
        selected_item = self.command_list.currentItem()
        if selected_item:
            command_text = selected_item.text()
            parts = command_text.split(", ")
            prefix = parts[0].split(": ")[1]
            value = parts[1].split(": ")[1]
            command = parts[2].split(": ")[1]
            window_str = parts[3].split(": ")[1]
            open_window = 1 if window_str == 'Yes' else 0
            self.db_cursor.execute(
                "DELETE FROM actions WHERE prefix = ? AND value = ? AND command = ? AND open_window = ?",
                (prefix, value, command, open_window)
            )
            self.db_cursor.connection.commit()
            self.load_commands()

class SimpleActionWindow(QtWidgets.QWidget):
    def __init__(self, hotkey_callback=None):
        super().__init__()
        self.setWindowTitle("Quick Action")
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setFixedSize(1000, 160)
        layout = QtWidgets.QHBoxLayout(self)
        self.input = QtWidgets.QLineEdit(self)
        self.input.setPlaceholderText("Type here...")
        self.input.setMinimumHeight(60)
        font = self.input.font()
        font.setPointSize(20)
        self.input.setFont(font)
        self.input.setStyleSheet("background: #111; color: #fff; border-radius: 10px; padding: 10px;")
        layout.addWidget(self.input)
        self.enter_btn = QtWidgets.QPushButton("Enter", self)
        self.enter_btn.setMinimumHeight(60)
        self.enter_btn.setFont(font)
        self.enter_btn.clicked.connect(self.handle_enter)
        self.enter_btn.setStyleSheet("background: #222; color: #fff; border-radius: 10px; padding: 10px;")
        layout.addWidget(self.enter_btn)
        self.setLayout(layout)
        self.setStyleSheet("background: #222; border-radius: 60px; overflow: hidden;")
        # Remove translucent background for solid color
        if self.testAttribute(QtCore.Qt.WA_TranslucentBackground):
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.voice_thread = None
        self.listening = False
        self.hotkey_callback = hotkey_callback

        # SQLite3 setup
        self.db_connection = sqlite3.connect("actions.db")
        self.db_cursor = self.db_connection.cursor()
        self.setup_database()

    def setup_database(self):
        # DB Management UI
        self.db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY,
            prefix TEXT NOT NULL,
            value TEXT NOT NULL,
            command TEXT NOT NULL
        )
        """)
        self.db_connection.commit()

        # Add open_window column if it doesn't exist
        self.db_cursor.execute("PRAGMA table_info(actions)")
        columns = [row[1] for row in self.db_cursor.fetchall()]
        if 'open_window' not in columns:
            self.db_cursor.execute("ALTER TABLE actions ADD COLUMN open_window INTEGER NOT NULL DEFAULT 1")
            self.db_connection.commit()

    def showEvent(self, event):
        super().showEvent(event)
        self.input.setFocus()
        self.center_window()
        self.listening = True
        self.start_voice_recognition()
        self.setFocus()

    def center_window(self):
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = int(screen.height() * 0.6) - self.height() // 2  # a bit more down
        self.move(x, y)

    def start_voice_recognition(self):
        import speech_recognition as sr
        from PyQt5.QtCore import QThread, pyqtSignal
        class VoiceInputThread(QThread):
            result_signal = pyqtSignal(str)
            def __init__(self, parent=None):
                super().__init__(parent)
                self._running = True
            def run(self):
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    while self._running:
                        try:
                            audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)
                            # Try German first, then English
                            try:
                                text = recognizer.recognize_google(audio, language='de-DE')
                            except Exception:
                                text = recognizer.recognize_google(audio, language='en-US')
                            # Convert number words to digits
                            text = self.words_to_numbers(text)
                            self.result_signal.emit(text)
                        except Exception:
                            continue
            def stop(self):
                self._running = False
            def words_to_numbers(self, text):
                # Simple mapping for German and English numbers 0-20
                num_map = {
                    'null': '0', 'eins': '1', 'zwei': '2', 'drei': '3', 'vier': '4', 'fünf': '5', 'sechs': '6', 'sieben': '7', 'acht': '8', 'neun': '9', 'zehn': '10',
                    'elf': '11', 'zwölf': '12', 'dreizehn': '13', 'vierzehn': '14', 'fünfzehn': '15', 'sechzehn': '16', 'siebzehn': '17', 'achtzehn': '18', 'neunzehn': '19', 'zwanzig': '20',
                    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
                    'eleven': '11', 'twelve': '12', 'thirteen': '13', 'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17', 'eighteen': '18', 'nineteen': '19', 'twenty': '20'
                }
                for word, digit in num_map.items():
                    text = text.replace(f" {word} ", f" {digit} ")
                    text = text.replace(f" {word}", f" {digit}")
                    text = text.replace(f"{word} ", f"{digit} ")
                    if text == word:
                        text = digit
                return text
        if self.voice_thread:
            self.voice_thread.stop()
        self.voice_thread = VoiceInputThread()
        self.voice_thread.result_signal.connect(self.set_input_text)
        self.voice_thread.start()

    def set_input_text(self, text):
        if text:
            current = self.input.text()
            if current:
                self.input.setText(current + ' ' + text)
            else:
                self.input.setText(text)
            self.input.setFocus()

    def execute_action(self):
        input_text = self.input.text()
        prefix, value = self.parse_input(input_text)
        self.db_cursor.execute("SELECT command, open_window FROM actions WHERE prefix = ? AND value = ?", (prefix, value))
        actions = self.db_cursor.fetchall()
        for cmd, open_window in actions:
            if open_window:
                # Open each command in a new cmd window and keep it open
                subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
            else:
                # Run quietly without opening a window
                subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        # Close the quick action window after launching commands
        self.close()

    def parse_input(self, input_text):
        # Example parsing logic: split by space and return prefix and value
        parts = input_text.split(" ", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return input_text, ""

    def handle_enter(self):
        input_text = self.input.text()
        if input_text == "11":
            self.open_management_window()
        else:
            self.execute_action()
        self.input.clear()

    def open_management_window(self):
        self.management_window = DatabaseManagementWindow(self.db_cursor)
        self.management_window.show()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self.handle_enter()
        elif event.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.listening = False
        if self.hotkey_callback:
            self.hotkey_callback(enable=True)
        super().closeEvent(event)

    def toggle_visibility(self):
        if self.isVisible():
            self.input.clear()
            self.close()
        else:
            self.input.clear()
            self.show()
            self.raise_()
            self.activateWindow()
            self.input.setFocus()

    def mousePressEvent(self, event):
        global_pos = self.mapToGlobal(event.pos())
        if not self.geometry().contains(global_pos):
            self.input.clear()
            self.close()
        else:
            super().mousePressEvent(event)

    def focusOutEvent(self, event):
        self.input.clear()
        self.close()
        super().focusOutEvent(event)

    def contextMenuEvent(self, event):
        # Prevent the default window menu from appearing
        event.ignore()

class AppController(QtCore.QObject):
    toggle_signal = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # Keep app running
        self.window = SimpleActionWindow()
        self.toggle_signal.connect(self.window.toggle_visibility)
        self.hotkey_thread = threading.Thread(target=self.register_hotkey, daemon=True)
        self.hotkey_thread.start()

    def register_hotkey(self):
        import keyboard
        print("Registering hotkey: alt+space")
        keyboard.add_hotkey('alt+space', self.emit_toggle, suppress=True)
        keyboard.wait()

    def emit_toggle(self):
        print("Hotkey pressed!")
        self.toggle_signal.emit()

    def toggle_window(self):
        print(f"Toggling window. Visible: {self.window.isVisible()}")
        if self.window.isVisible():
            self.window.close()
        else:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
            self.window.input.setFocus()

    def run(self):
        print("App event loop starting...")
        self.setup_database_ui()
        sys.exit(self.app.exec_())

    def setup_database_ui(self):
        self.database_window = DatabaseManagementWindow(self.window.db_cursor)

if __name__ == "__main__":
    print("Press 'Alt + Space' to open the quick action window.")
    controller = AppController()
    controller.run()
