import puzzlepiece as pzp
from pyqtgraph.Qt import QtWidgets

class Piece(pzp.Piece):
    def __init__(self, puzzle):
        # Move the custom_layout to the right of the generated inputs
        super().__init__(puzzle)

        ctr_ports = ["CTR0", "CTR1", "CTR2"]
        self.params["counter"].input.addItems(ctr_ports)

        pfi_ports = ["PFI12", "PFI11", "PFI10"]
        self.params["PFI port"].input.addItems(pfi_ports)

    def define_params(self):
        # Set on-board counter
        @pzp.param.dropdown(self, 'counter', '')
        def counter(self):
            return None

        @counter.set_setter(self)
        def counter(self, value):
            self.params["armed"].set_value(False)
            return value

        # Set PFI output port
        @pzp.param.dropdown(self, 'PFI port', '')
        def pfi_port(self):
            return None

        @pfi_port.set_setter(self)
        def pfi_port(self, value):
            self.params["armed"].set_value(False)
            return value
    
        @pzp.param.spinbox(self, "Rep rate", 1.0)
        def rep_rate(self, value):
            self.params["armed"].set_value(False)
            
        # Set the channels and rep. rate 
        @pzp.param.checkbox(self, "armed", 0)
        def armed(self, value):
            if self.puzzle.debug:
                self.params["Unlock"].set_value(False)
                return value
            current_value = self.params['armed'].value
            if value and not current_value:
                max_freq = self.params["Rep rate"].get_value() * 1e3
                period = 1/max_freq
                self.puzzle["NIDAQ"].daq.add_pulse_output("laser_trigger", "ctr0", "pfi12", kind='time', on=period/2, off=period/2, clk_src=None, continuous=True, samps=1)
                return True
            self.params["Unlock"].set_value(False)
            return False

        #  Safety precaution - Trigger unlock button
        @pzp.param.checkbox(self, "Unlock", False, visible=True)
        def unlock(self, value):
            current_value = self.params['Unlock'].value
            if value and not current_value:
                self._ensure_armed()
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
                    # Start infinite pulse train
                    print("-- Laser Firing")
                    self.params["FIRE LASER"].input.setStyleSheet("background-color: #ff0000")
                    self.puzzle["NIDAQ"].daq.set_pulse_output("laser_trigger", continuous=True)
                    self.puzzle["NIDAQ"].daq.start_pulse_output(names="laser_trigger", autostop=False)
                    return True
                except Exception as e:
                    self.kill_laser_output()
                    self.params["FIRE LASER"].input.setStyleSheet("background-color: #f3f3f3")
                    raise e
                
            elif current_value:
                # Stop pulse train
                print("-- Laser stopped")
                self.kill_laser_output()
                self.params["FIRE LASER"].input.setStyleSheet("background-color: #f3f3f3")
                return False

        pzp.param.spinbox(self, "pulses", 1, v_min=1)(None)

    def define_actions(self):
        @pzp.action.define(self, "Send pulse train")
        @self._ensure_daq
        @self._ensure_unlocked
        def trigger_pulse(self):
            if not self.puzzle.debug:
                self.puzzle["NIDAQ"].daq.set_pulse_output("laser_trigger", continuous=False, samps=1)
                for _ in range(int(self.params["pulses"].value)):
                    self.puzzle["NIDAQ"].daq.start_pulse_output(names="laser_trigger", autostop=True)

    # Ensure devices are connected
    @pzp.piece.ensurer        
    def _ensure_daq(self):
        if not self.puzzle.debug:
            self.puzzle["NIDAQ"]._ensure_connected()

    @pzp.piece.ensurer        
    def _ensure_armed(self):
        if not self.params["armed"].value:
            raise Exception("Arm trigger output port settings first")

    @pzp.piece.ensurer        
    def _ensure_unlocked(self):
        if not self.params["Unlock"].value:
            raise Exception("Unlock laser trigger first")

    def kill_laser_output(self):
        if not self.puzzle.debug:
            self.puzzle["NIDAQ"].daq.stop_pulse_output(names="laser_trigger")

if __name__ == "__main__":
    import NIDAQ
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Lab", debug=True)
    puzzle.add_piece("NIDAQ", NIDAQ.Piece(puzzle), 0, 0)
    puzzle.add_piece("Spot laser", Piece(puzzle), 1, 0)
    puzzle.show()
    app.exec()

