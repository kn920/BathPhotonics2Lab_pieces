import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets
import pyqtgraph as pg
import serial
import serial.tools.list_ports
import datetime

class Piece(pzp.Piece):
    def __init__(self, puzzle):
        # Move the custom_layout to the right of the generated inputs
        super().__init__(puzzle, custom_horizontal=True)
    
    def define_params(self):

        # Set COM port
        @pzp.param.dropdown(self, 'COM', '')
        def com(self):
            return None
        
        @com.set_getter(self)
        def com(self):
                if self.puzzle.debug:
                    ports = ["COM 3", "COM 4", "COM 5"]
                else:
                    ports_detailed = serial.tools.list_ports.comports()
                    ports = [ p for p, _, _ in sorted(ports_detailed)]
                self["COM"].input.clear()
                self["COM"].input.addItems(ports)    

        @com.set_setter(self)
        def com(self, value):
            return value

        # Connect to device
        @pzp.param.checkbox(self, "connected", 0)
        def connect(self, value):
            if self.puzzle.debug:
                self.params["status"].get_value()
                return value
            
            # Check if we're currently connected by checking what the state of the checkbox was
            current_value = self.params['connected'].value
            if value and not current_value:
                try:
                    self.SerialObj = serial.Serial(port=self.params["COM"].value, timeout=0.3)
                    # self.params["status"].get_value()

                    return 1
                except Exception as e:
                    self.dispose()
                    raise e
                
            elif current_value:
                # Disconnect
                self.dispose()
                return 0

        ### Need to decode - list()?
        # Readout status
        @pzp.param.readout(self, "status")
        @self._ensure_connected
        def status(self):
            if not self.puzzle.debug:
                self.params["timestamp"].set_value(datetime.datetime.now().strftime(f"%d/%m/%Y\n %H:%M:%S"))
                line = self.actions["readline"]()
                return line
            self.params["timestamp"].set_value(datetime.datetime.now().strftime(f"%d/%m/%Y\n %H:%M:%S"))
            return "debug mode"
        
        # Readout timestamp
        pzp.param.readout(self, "timestamp")(None)

    def define_actions(self):
        @pzp.action.define(self, 'readline', visible=False)
        def readline(self):
            if not self.puzzle.debug:
                value = self.SerialObj.readline().decode('utf-8', errors='ignore')
                # print(repr(value))
                if value == "....":
                    value = "RAMPING"
                if value == "\r\x11\x13*\r\n" or value == "\x11" or value == "\x13":
                    return self.params["status"].value
                elif "\x13" in value:
                    value = value.strip("\x11").strip("\x13")
                if value:
                    return value
                return self.params["status"].value

        ### write to the COM need "\n" or "\r"?
        @pzp.action.define(self, 'power up')
        @self._ensure_connected
        def power_up(self):
            if not self.puzzle.debug:
                self.SerialObj.write(('+\n').encode('utf-8'))
            self.params["status"].get_value()
            
        @pzp.action.define(self, 'power down')
        @self._ensure_connected
        def power_down(self):
            if not self.puzzle.debug:
                self.SerialObj.write(('-\n').encode('utf-8'))
            self.params["status"].get_value()

        @pzp.action.define(self, 'ping')
        @self._ensure_connected
        def ping(self):
            if not self.puzzle.debug:
                self.SerialObj.write(('?\n').encode('utf-8'))
            self.params["status"].get_value()

    # Ensure devices are connected
    @pzp.piece.ensurer        
    def _ensure_connected(self):
        if not self.puzzle.debug and not hasattr(self, 'SerialObj'):
            raise Exception("Laser not connected")

    def dispose(self):
        if hasattr(self, 'SerialObj'):
            self.SerialObj.close()
            del self.SerialObj

    # Disconnect the camera when window close
    def handle_close(self, event):
        self.dispose()


    def custom_layout(self):
        layout = QtWidgets.QGridLayout()
        # Add a PuzzleTimer for live view
        delay = 1.5          # CHECK - Change to smaller value for faster refresh, but stable
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle,  self.params["status"].get_value, delay)
        layout.addWidget(self.timer)
        return layout

    def call_stop(self):
        self.timer.stop()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Lab", debug=False)
    puzzle.add_piece("Spot laser", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()
