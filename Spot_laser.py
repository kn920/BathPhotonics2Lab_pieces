import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets
import serial
import serial.tools.list_ports
import time
import datetime

class Piece(pzp.Piece):
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
                    self.SerialObj = serial.Serial(self.params["COM"].value())
                    self.SerialObj.baudrate = 9600  # Set Baud rate to 9600
                    self.SerialObj.bytesize = 8   # Number of data bits = 8
                    self.SerialObj.parity  ='N'   # No parity
                    self.SerialObj.stopbits = 1   # Number of Stop bits = 1
                    self.SerialObj.timeout = 5   # Set timeout to 5 seconds
                    self.params["status"].get_value()

                    return 1
                except Exception as e:
                    self.dispose()
                    raise e
                
            elif current_value:
                # Disconnect
                self.dispose()
                return 0

        # Readout status
        @pzp.param.readout(self, "status")
        @self._ensure_connected
        def status(self):
            if not self.puzzle.debug:
                self.params["timestamp"].set_value(datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"))
                return self.SerialObj.readline()
            self.params["timestamp"].set_value(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            return "debug mode"
        
        # Readout timestamp
        @pzp.param.readout(self, "timestamp")
        @self._ensure_connected
        def timestamp(self):
            return self.params["timestamp"].value
        
        @timestamp.set_setter(self)
        def timestamp(self, value):
            return value

    def define_actions(self):

        @pzp.action.define(self, 'power up')
        @self._ensure_connected
        def power_up(self):
            if not self.puzzle.debug:
                self.SerialObj.write(b'+')
            self.params["status"].get_value()
            
        @pzp.action.define(self, 'power down')
        @self._ensure_connected
        def power_down(self):
            if not self.puzzle.debug:
                self.SerialObj.write(b'-')
            self.params["status"].get_value()

        @pzp.action.define(self, 'ping')
        @self._ensure_connected
        def ping(self):
            if not self.puzzle.debug:
                self.SerialObj.write(b'?')
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

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Lab", debug=True)
    puzzle.add_piece("Spot laser", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()