import numpy as np
from time import sleep
from qtpy import QtWidgets
import pyqtgraph as pg
from pyqtgraph.graphicsItems.NonUniformImage import NonUniformImage

import puzzlepiece as pzp
import datasets as ds
import datetime


class Piece(pzp.Piece):
    def __init__(self, puzzle=None, custom_horizontal=True, *args, **kwargs):
        super().__init__(puzzle, custom_horizontal, *args, **kwargs)

    def define_params(self):
        pzp.param.text(self, "vary", "AOM:mod_in")(None)
        pzp.param.spinbox(self, "start", 0.0)(None)
        pzp.param.spinbox(self, "end", 5.0)(None)
        pzp.param.spinbox(self, "N", 40)(None)
        pzp.param.text(self, "filename", "data/ll.ds")(None)
        pzp.param.progress(self, "progress")(None)


    def _take_ll(self, param_image, param_subBG, action_takeBG, param_BG, pulse_train_param, wl, param_hw_trigger):
        positions = np.linspace(self["start"].value, self["end"].value, self["N"].value)
        vary = pzp.parse.parse_params(self["vary"].value, self.puzzle)[0]

        # Make sure the laser is not free-running
        if pulse_train_param:
            pulse_train_param.set_value(0)
        vary.set_value(positions[0])

        # Get background
        action_takeBG()
        background = param_BG.value
        self.puzzle.process_events()
        
        param_subBG.set_value(False)
        # Make empty arrays for the values
        spectra = np.zeros((len(positions), *background.shape), np.int32)
        powers = np.zeros(len(positions))
        
        if param_hw_trigger.value:
            # Keep laser off, ready to trigger
            pulse_train_param.set_value(0)
        else:
            # Free-running laser
            pulse_train_param.set_value(1)

        # Scan position and save the spectra
        self.stop = False
        for i, pos in enumerate(self["progress"].iter(positions)):
            if pos < vary.input.minimum() or pos > vary.input.maximum():
                pulse_train_param.set_value(0)
                raise Exception("Scan range over the limits")
            vary.set_value(pos)

            if param_hw_trigger.value:
                spectra[i] = self.puzzle["Andor"].single_acquisition()
            else:
                spectra[i] = param_image.get_value()
            # powers[i] = self.puzzle['powermeter']['power'].get_value()
            if self.stop:
                pulse_train_param.set_value(0)
                raise Exception("User interruption")
            self.puzzle.process_events()

        # Stop triggering laser
        pulse_train_param.set_value(0)

        spectra = spectra[:i+1]
        powers = powers[:i+1]
        
        # Make a dataset for the data
        ll = ds.dataset(spectra, aom_voltage=np.asarray(positions), pixel=np.arange(spectra.shape[1]), wl=wl)
        ll.metadata['background'] = background
        ll.metadata['hardware trigger'] = param_hw_trigger.value
        self.result = ll
        
        self.update_plot(ll)
        self.elevate()
        
        param_subBG.set_value(True)

        return ll

    def define_actions(self):
        @pzp.action.define(self, "Scan")
        def scan(self):
            ll = self._take_ll(
                self.puzzle["Andor"]["image"],
                self.puzzle["Andor"]["sub_background"],
                self.puzzle["Andor"].actions["Take background"],
                self.puzzle["Andor"]["background"],
                self.puzzle["Spot trigger"]["FIRE LASER"],
                self.puzzle["Andor"]["wls"].value,
                self.puzzle["Spot trigger"]["Hardware trigger"]
            )
            self.puzzle.record_values(  "Andor:exposure, Andor:grating, Andor:centre, Andor:FVB mode, " \
                                        "Andor:amp_mode, Andor:vs_speed, Andor:slit_width", 
                                        ll.metadata)
            ll.metadata["timestamp"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            ll.save(pzp.parse.format(self["filename"].value, self.puzzle), 2)
        
    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        self.gl = pg.GraphicsLayoutWidget()
        layout.addWidget(self.gl)

        self.plot1 = self.gl.addPlot(0, 0)
        self.plot2 = self.gl.addPlot(0, 1)
        self.plot_line1 = self.plot2.plot()
        self.plot3 = self.gl.addPlot(0, 2)
        self.plot3.setLogMode(True, True)
        self.plot_line2 = self.plot3.plot()

        return layout
    
    def update_plot(self, ll):
        values = ll.take_sum('pixel').raw.astype(float) - np.sum(ll.metadata['background'].astype(float), axis=0)
        values /= np.amax(values, axis=1).reshape((-1, 1))
        self.plot1.clear()
        # try:
        #     nui = NonUniformImage(ll.wl, ll.power, values.T)
        #     self.plot1.addItem(nui)
        # except:
        ui = pg.ImageItem(values.T)
        self.plot1.addItem(ui)
        self.plot_line1.setData(ll.aom_voltage, ll.take_sum('pixel').take_sum('wl').raw - np.sum(ll.metadata['background']))
        self.plot_line2.setData(ll.aom_voltage, ll.take_sum('pixel').take_sum('wl').raw - np.sum(ll.metadata['background']))


if __name__ == "__main__":
    import Andor, Spot_trigger, AOM, NIDAQ
    app = pzp.QApp([])
    puzzle = pzp.Puzzle(debug=True)
    puzzle.add_piece("Andor", Andor.LineoutPiece(puzzle), 0, 0, 2, 1)
    puzzle.add_piece("ll", Piece(puzzle), 2, 0)
    puzzle.add_piece("NIDAQ", NIDAQ.Piece(puzzle), 0, 1)
    puzzle.add_piece("Spot trigger", Spot_trigger.Piece(puzzle), 1, 1)
    puzzle.add_piece("AOM", AOM.Piece(puzzle), 2, 1)    
    puzzle.show()
    app.exec()