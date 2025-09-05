import sys
import serial
import serial.tools.list_ports
import puzzlepiece as pzp
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QThread
import datetime


# --- Background reader thread ---
class SerialReader(QtCore.QThread):
    data_received = QtCore.pyqtSignal(str)

    def __init__(self, ser):
        super().__init__()
        self.ser = ser
        self._running = True

    def run(self):
        while self._running and self.ser.is_open:
            if self.ser.in_waiting:
                try:
                    data = self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                    self.data_received.emit(data)
                except Exception as e:
                    self.data_received.emit(f"\n[Error: {e}]\n")

    def stop(self):
        self._running = False
        self.wait()


# --- Terminal input/output widget ---
class TerminalWidget(QtWidgets.QPlainTextEdit):
    key_pressed = QtCore.pyqtSignal(str)   # use QtCore from pyqtgraph

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet("background-color: black; color: white; font-family: monospace;")

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Backspace:
            self.key_pressed.emit("\b")
        elif key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.key_pressed.emit("\r")
        elif event.text():
            self.key_pressed.emit(event.text())
        super().keyPressEvent(event)


class Settings(pzp.piece.Popup):
    def define_params(self):
        super().define_params()
        self.add_child_params(["Baud", "Data bits", "Parity", "Stop bits", "Line ending", "Local echo"])
        # Reload dropdown lists when Settings popup opened
        def relaod_dropdowns():    
            self["Baud"].input.addItems(["9600", "19200", "38400", "57600", "115200"])
            self["Data bits"].input.addItems(["5", "6", "7", "8"])
            self["Parity"].input.addItems(["N", "E", "O", "M", "S"])
            self["Stop bits"].input.addItems(["1", "1.5", "2"])
            self["Line ending"].input.addItems(["None", "CR", "LF", "CR+LF"])

            self["Baud"].get_value()
            self["Data bits"].get_value()
            self["Parity"].get_value()
            self["Stop bits"].get_value()
            self["Line ending"].get_value()
            self["Local echo"].get_value()

        relaod_dropdowns()

    def get_settings(self):
        return {
            "baud": int(self.baud.currentText()),
            "databits": int(self.databits.currentText()),
            "parity": self.parity.currentText(),
            "stopbits": float(self.stopbits.currentText()),
            "lineending": self.lineending.currentIndex(),
            "localecho": self.localecho.isChecked(),
        }


# --- Puzzlepiece Serial Terminal Piece ---
class Piece(pzp.Piece):
    def define_params(self):

        # List and select device indices
        @pzp.param.dropdown(self, "Serial port", "")
        def device_idx(self):
            return None
        
        @device_idx.set_getter(self)
        def device_idx(self):
            self["Serial port"].input.clear()
            for port in serial.tools.list_ports.comports():
                self["Serial port"].input.addItem(port.device)
            self["Serial port"].input.addItems(["loop:// (virtual)"])
            return self.params['Serial port'].value


        @pzp.param.checkbox(self, "connected", 0)
        def connect(self, value):
            current_value = self.params['connected'].value
            if value and not current_value:
                try:
                    self._connect_serial()
                    return 1
                except Exception as e:
                    self.dispose()
                    raise e
            elif current_value and not value:
                self.dispose()
                return 0
        
        @pzp.param.dropdown(self, "Baud", "9600", visible=False)
        def baud(self):
            return None
        
        @baud.set_setter(self)
        def baud(self, value):
            return value
        
        @pzp.param.dropdown(self, "Data bits", "8", visible=False)
        def databits(self):
            return None
        
        @databits.set_setter(self)
        def databits(self, value):
            return value
        
        @pzp.param.dropdown(self, "Parity", "N", visible=False)
        def parity(self):
            return None
        
        @parity.set_setter(self)
        def parity(self, value):
            return value
        
        @pzp.param.dropdown(self, "Stop bits", "1", visible=False)
        def stopbits(self):
            return None
        
        @stopbits.set_setter(self)
        def stopbits(self, value):
            return value
        
        @pzp.param.dropdown(self, "Line ending", "None", visible=False)
        def lineending(self):
            return None
        
        @lineending.set_setter(self)
        def lineending(self, value):
            return value
        
        pzp.param.checkbox(self, "Local echo", False, visible=False)(None)

    def define_actions(self):
        @pzp.action.define(self, "Settings")
        @self._ensure_disconnected
        def settings(self):
            self.open_popup(Settings, "More settings")

    @pzp.piece.ensurer
    def _ensure_connected(self):
        if not self.puzzle.debug and not hasattr(self, 'ser'):
            raise Exception("Serial not connected")
        
    @pzp.piece.ensurer
    def _ensure_disconnected(self):
        if not self.puzzle.debug and hasattr(self, 'ser'):
            raise Exception("Disconnect the Serial first")

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # Terminal inside a QWidget container
        terminal_container = QtWidgets.QWidget()
        term_layout = QtWidgets.QVBoxLayout(terminal_container)
        self.terminal = TerminalWidget()
        self.terminal.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.terminal.key_pressed.connect(self.send_key)
        term_layout.addWidget(self.terminal)
        layout.addWidget(terminal_container)

        # Timestamp label
        self.timestamp_label = QtWidgets.QLabel(datetime.datetime.now().strftime(f"%d/%m/%Y\t %H:%M:%S"), alignment=QtCore.Qt.AlignRight)
        layout.addWidget(self.timestamp_label)

        # Timer for counter
        self.timestamp = QtCore.QTimer(self)
        self.timestamp.timeout.connect(self.update_timestamp)
        self.timestamp.start(200)

        # Default settings
        self.session_settings = {
            "baud": 115200,
            "databits": 8,
            "parity": "N",
            "stopbits": 1,
            "lineending": 0,
            "localecho": False,
        }

        return layout

    def append_text(self, text):
        # move cursor to the end, insert text, then move again
        self.terminal.moveCursor(QtGui.QTextCursor.End)
        self.terminal.insertPlainText(text)
        self.terminal.moveCursor(QtGui.QTextCursor.End)


    def _connect_serial(self):
        port = self.params["Serial port"].value
        if port.startswith("loop://"):
            self.ser = serial.serial_for_url("loop://", baudrate=int(self["Baud"].get_value()), timeout=0)
        else:
            self.ser = serial.Serial(
                port,
                baudrate=int(self["Baud"].get_value()),
                bytesize=int(self["Data bits"].get_value()),
                parity=self["Parity"].get_value(),
                stopbits=int(self["Stop bits"].get_value()),
                timeout=0,
            )
        self.reader = SerialReader(self.ser)
        self.reader.data_received.connect(self.append_text)
        self.reader.start()
        self.terminal.appendPlainText(f"[Connected to {port}]\n")

    def send_key(self, char):
        if hasattr(self, 'ser') and self.ser.is_open:
            # Apply line ending rules
            if char == "\r":
                lineend = self["Line ending"].get_value()
                if lineend == "CR":  # CR
                    data = "\r"
                elif lineend == "LF":  # LF
                    data = "\n"
                elif lineend == "CR+LF":  # CR+LF
                    data = "\r\n"
                else:
                    data = ""
                if data:
                    self.ser.write(data.encode())
            elif char == "\b":
                self.ser.write(b"\b")
            else:
                self.ser.write(char.encode())

    def update_timestamp(self):
        self.timestamp_label.setText(datetime.datetime.now().strftime(f"%d/%m/%Y\t %H:%M:%S"))

    def dispose(self):
        if hasattr(self, "reader"):
            self.reader.stop()
            del self.reader
        if hasattr(self, "ser"):
            self.ser.close()
            del self.ser

# --- Main entry ---
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    puzzle = pzp.Puzzle(app, "Lab", debug=False)
    puzzle.add_piece("SerialTerminal", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()
