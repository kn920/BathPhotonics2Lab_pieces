import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    def __init__(self, puzzle):
        # Move the custom_layout to the right of the generated inputs
        super().__init__(puzzle)

        ports = ["AO0", "AO1", "AO2"]
        self.params["AO port"].input.addItems(ports)
    
    def define_params(self):
        super().define_params()

        # Set analog output port
        @pzp.param.dropdown(self, 'AO port', '')
        def ao_port(self):
            return None

        @ao_port.set_setter(self)
        @self._ensure_daq
        def ao_port(self, value):
            if not self.puzzle.debug:
                self.puzzle["NIDAQ"].daq.add_voltage_output("AOM_mod_in", value.lower(), rng=(0, 5), initial_value=0.0)
            return value

        # Set mod_in voltage
        @pzp.param.spinbox(self, "mod_in", 0., v_min=0.0, v_max=5.0, v_step=0.5)
        @self._ensure_daq
        def mod_in(self, value):
            if self.puzzle.debug:
                return value
            # If we're connected and not in debug mode, set the mod_in voltage
            self.puzzle["NIDAQ"].daq.set_voltage_outputs("AOM_mod_in", value)

        @mod_in.set_getter(self)
        @self._ensure_daq
        def mod_in(self):
            if self.puzzle.debug:
                return self.params['mod_in'].value
            # If we're connected and not in debug mode, return the exposure from the camera
            return self.puzzle["NIDAQ"].daq.get_voltage_outputs("AOM_mod_in")[0]

    # Ensure devices are connected
    @pzp.piece.ensurer        
    def _ensure_daq(self):
        if not self.puzzle.debug:
            self.puzzle["NIDAQ"]._ensure_connected()

if __name__ == "__main__":
    import NIDAQ
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Lab", debug=True)
    puzzle.add_piece("NIDAQ", NIDAQ.Piece(puzzle), 0, 0)
    puzzle.add_piece("AOM", Piece(puzzle), 1, 0)
    puzzle.show()
    app.exec()
