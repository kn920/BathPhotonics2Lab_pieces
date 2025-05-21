import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    def __init__(self, puzzle):
        # Move the custom_layout to the right of the generated inputs
        super().__init__(puzzle)

        ctr_ports = ["CTR0", "CTR1", "CTR2"]
        self.params["counter"].input.addItems(ctr_ports)

        pfi_ports = ["PFI0", "PFI1", "PFI2"]
        self.params["PFI port"].input.addItems(pfi_ports)

    def define_params(self):
        # Set on-board counter
        @pzp.param.dropdown(self, 'counter', '')
        def counter(self):
            return None

        @counter.set_setter(self)
        def counter(self, value):
            return value

        # Set PFI output port
        @pzp.param.dropdown(self, 'PFI port', '')
        def pfi_port(self):
            return None

        @pfi_port.set_setter(self)
        def pfi_port(self, value):
            return value
    
        #  Safety precaution - Trigger unlock button
        @pzp.param.checkbox(self, "Unlock", False, visible=True)
        def unlock(self, value):
            current_value = self.params['Unlock'].value
            if value and not current_value:
                self.params["Unlock"].input.setStyleSheet("background-color: #fffba0")
                return True
            elif current_value:
                self.params["FIRE LASER"].set_value(False)
                self.params["Unlock"].input.setStyleSheet("background-color: #f3f3f3")
                return False

        @pzp.param.checkbox(self, "FIRE LASER", False)
        @self._ensure_daq
        @self._ensure_unlocked
        def pulse_train(self, value):
            if self.puzzle.debug:
                if value:
                    self.params["FIRE LASER"].input.setStyleSheet("background-color: #ff0000")
                else:
                    self.params["FIRE LASER"].input.setStyleSheet("background-color: #f3f3f3")
                return value
            
            # Check if we're already firing pulse train by checking what the state of the checkbox was
            current_value = self.params['FIRE LASER'].value
            if value and not current_value:
                try:
                    # Start pulse train
                    print("fire!!")
                    self.params["FIRE LASER"].input.setStyleSheet("background-color: #ff0000")
                    self.daq.set_pulse_output("laser_trigger", continuous=True)
                    self.daq.start_pulse_output(names="laser_trigger", autostop=False)
                    return True
                except Exception as e:
                    self.kill_laser_output()
                    self.params["FIRE LASER"].input.setStyleSheet("background-color: #f3f3f3")
                    raise e
                
            elif current_value:
                # Stop pulse train
                print("Stopping!")
                self.kill_laser_output()
                self.params["FIRE LASER"].input.setStyleSheet("background-color: #f3f3f3")
                return False


    def define_actions(self):
        @pzp.action.define(self, "Trigger pulse")
        @self._ensure_daq
        @self._ensure_unlocked
        def trigger_pulse(self):
            print('pulse')
            if not self.puzzle.debug:
                self.daq.set_pulse_output("laser_trigger", continuous=False, samps=1)
                self.daq.start_pulse_output(names="laser_trigger", autostop=True)


    # Ensure devices are connected
    @pzp.piece.ensurer        
    def _ensure_daq(self):
        if not self.puzzle.debug:
            self.puzzle["NIDAQ"]._ensure_connected()

    @pzp.piece.ensurer        
    def _ensure_unlocked(self):
        if not self.params["Unlock"].value:
            raise Exception("Unlock laser trigger first")

    def setup(self):
        max_freq = 50e3
        period = 1/max_freq
        self.daq.add_pulse_output("laser_trigger", "ctr0", "pfi0", kind='time', on=period/2, off=period/2, clk_src=None, continuous=True, samps=1)

    def kill_laser_output(self):
        if not self.puzzle.debug:
            self.daq.stop_pulse_output(names="laser_trigger")

if __name__ == "__main__":
    import NIDAQ
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Lab", debug=True)
    puzzle.add_piece("NIDAQ", NIDAQ.Piece(puzzle), 0, 0)
    puzzle.add_piece("Spot laser", Piece(puzzle), 1, 0)
    puzzle.show()
    app.exec()
