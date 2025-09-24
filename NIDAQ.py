import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets
from pylablib.devices import NI

class Piece(pzp.Piece):  
    def define_params(self):

        # Connect to NI-DAQ
        @pzp.param.checkbox(self, "connected", 0)
        def connect(self, value):
            if self.puzzle.debug:
                self.daq = NI.NIDAQ("Dev1")
                return value
            
            # Check if we're currently connected by checking what the state of the checkbox was
            current_value = self.params['connected'].value
            if value and not current_value:
                try:
                    self.daq = NI.NIDAQ("Dev1")
                    if not self.daq.is_opened():
                        raise Exception("NI DAQ not connected")
                    return 1
                except Exception as e:
                    self.dispose()
                    raise e
                
            elif current_value and not value:
                # Disconnect
                self.dispose()
                return 0

    # Ensure devices are connected
    @pzp.piece.ensurer        
    def _ensure_connected(self):
        if not self.puzzle.debug and not hasattr(self, 'daq'):
            raise Exception("NI DAQ not connected")

    def dispose(self):
        if hasattr(self, 'daq'):
            self.daq.close()
            del self.daq

    # Disconnect the DAQ when window close
    def handle_close(self, event):
        self.dispose()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Lab", debug=False)
    puzzle.add_piece("NIDAQ", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()
