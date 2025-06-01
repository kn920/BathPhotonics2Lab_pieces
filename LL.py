import numpy as np
from time import sleep
from qtpy import QtWidgets
import pyqtgraph as pg
from pyqtgraph.graphicsItems.NonUniformImage import NonUniformImage

import puzzlepiece as pzp
from datasetsuite import datasets as ds
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


    def _take_ll(self, image_param, pulse_train_param, wl):
        positions = np.linspace(self["start"].value, self["end"].value, self["N"].value)
        vary = pzp.parse.parse_params(self["vary"].value, self.puzzle)[0]

        # Make sure the laser is not free-running
        if pulse_train_param:
            pulse_train_param.set_value(0)
        vary.set_value(positions[0])

        # Get background
        background = image_param.get_value()
        self.puzzle.process_events()
        
        # Make empty arrays for the values
        spectra = np.zeros((len(positions), *background.shape), np.ushort)
        powers = np.zeros(len(positions))
        
        # Free-running laser
        pulse_train_param.set_value(1)

        # Scan position and save the spectra
        self.stop = False
        for i, pos in enumerate(self["progress"].iter(positions)):
            if pos < vary.input.minimum() or pos > vary.input.maximum():
                pulse_train_param.set_value(0)
                raise Exception("Scan range over the limits")
            vary.set_value(pos)
            spectra[i] = image_param.get_value()
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
        # ll.metadata['positions'] = np.asarray(positions)
        # self.puzzle.record_values("powermeter:wavelength, powermeter:avg_time", ll.metadata)
        self.result = ll
        
        self.update_plot(ll)
        self.elevate()

        return ll

    def define_actions(self):
        @pzp.action.define(self, "Scan")
        def scan(self):
            ll = self._take_ll(
                self.puzzle["Andor"]["image"],
                self.puzzle["Spot trigger"]["FIRE LASER"],
                self.puzzle["Andor"]["wls"].value
            )
            ll.metadata["timestamp"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            self.puzzle.record_values("Andor:exposure, Andor:grating, Andor:amp_mode, Andor:vs_speed, Andor:slit_width", 
                                      ll.metadata)
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
        self.plot_line1.setData(ll.aom_voltage, ll.take_sum('pixel').take_sum('wl').raw.astype(int) - np.sum(ll.metadata['background'].astype(int)))
        self.plot_line2.setData(ll.aom_voltage, ll.take_sum('pixel').take_sum('wl').raw.astype(int) - np.sum(ll.metadata['background'].astype(int)))


if __name__ == "__main__":
    import Andor, Spot_trigger, AOM
    app = pzp.QApp([])
    puzzle = pzp.Puzzle()
    puzzle.add_piece("Andor", Andor.LineoutPiece(puzzle), 0, 0)
    puzzle.add_piece("ll", Piece(puzzle), 1, 0)
    puzzle.add_piece("Spot trigger", Spot_trigger.Piece(puzzle), 0, 1)
    puzzle.add_piece("AOM", AOM.Piece(puzzle), 1, 1)    
    puzzle.show()
    app.exec()