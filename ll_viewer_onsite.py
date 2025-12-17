import puzzlepiece as pzp
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import numpy as np
import datasets as ds
from scipy.io import loadmat
import mat73

class Piece(pzp.Piece):
    def __init__(self, puzzle, custom_horizontal=True, *args, **kwargs):
        super().__init__(puzzle, custom_horizontal, *args, **kwargs)
        # Set horizontal layout stretch: 1/5 left (params), 4/5 right (plots)
        self.layout.setStretch(0, 1)
        self.layout.setStretch(1, 4)
        
    def define_params(self):
        # Define readouts and controls (dropdowns, sliders, checkboxes)
        pzp.param.readout(self, "filename", visible=False)(None)
        pzp.param.readout(self, "name", visible=True)(None)
        pzp.param.readout(self, "datatype", visible=False)(None)
        pzp.param.dropdown(self, "DATA var", "", visible=True)(None)
        pzp.param.dropdown(self, "WL var", "", visible=True)(None)
        pzp.param.dropdown(self, "POWER var", "", visible=True)(None)
        pzp.param.dropdown(self, "BG var", "", visible=True)(None)
        pzp.param.array(self, 'Spectra', True)(None)
        pzp.param.array(self, 'Power', True)(None)
        pzp.param.array(self, 'Wavelength', True)(None)
        pzp.param.array(self, 'Background', True)(None)
        pzp.param.checkbox(self, "Log scale", False, visible=True)(None)
        pzp.param.checkbox(self, "Normalise", False, visible=True)(None)
        pzp.param.checkbox(self, "Sub. BG", False, visible=True)(None)
        pzp.param.array(self, "Norm Spectra", False)(None)
        pzp.param.slider(self, "Spectrum slider", 0, visible=True, v_step=1)(None)

        self["DATA var"].set_value("raw")
        self["WL var"].set_value("wl")
        self["POWER var"].set_value("aom_voltage")
        self["BG var"].set_value("background")

    def define_actions(self):
        # --- Load action ---
        @pzp.action.define(self, 'Load', visible=True)
        def Load(self):
            try:
                [self.raw_filename], _ = QtWidgets.QFileDialog.getOpenFileNames(
                    None, 'Open LL data', '', 'dataset data (*.ds);;MATLAB data (*.mat)')
            except ValueError:
                raise Exception("User Cancelled")
            
            if self.raw_filename:
                self["filename"].set_value(self.raw_filename)
                self["name"].set_value(self.raw_filename.split('/')[-1])
                self["datatype"].set_value(self.raw_filename.split('.')[-1])
                self.old_DATAvar = self["DATA var"].value
                self.old_WLvar = self["WL var"].value
                self.old_POWERvar = self["POWER var"].value
                self.old_BGvar = self["BG var"].value

                match self["datatype"].value:
                    case "ds":
                        self.dat = ds.load(self.raw_filename)
                        self["DATA var"].input.clear()
                        self["DATA var"].input.addItems(["raw"])
                        axes = self.dat.axes
                        self["WL var"].input.clear()
                        self["WL var"].input.addItems(axes)
                        self["POWER var"].input.clear()
                        self["POWER var"].input.addItems(axes)
                        self["BG var"].input.clear()
                        self["BG var"].input.addItems(self.dat.metadata.keys())
                        # Restore previous selection
                        if self.old_WLvar in axes: self["WL var"].set_value(self.old_WLvar)
                        if self.old_POWERvar in axes: self["POWER var"].set_value(self.old_POWERvar)
                        if self.old_BGvar in self.dat.metadata.keys(): self["BG var"].set_value(self.old_BGvar)
                    case "mat":
                        try:
                            self.dat = loadmat(self.raw_filename)
                        except:
                            self.dat = mat73.loadmat(self.raw_filename)
                        keys = list(self.dat.keys())
                        for k in ["DATA var","WL var","POWER var","BG var"]:
                            self[k].input.clear()
                            self[k].input.addItems(keys)
                        # Restore previous selection
                        if self.old_DATAvar in keys: self["DATA var"].set_value(self.old_DATAvar)
                        if self.old_WLvar in keys: self["WL var"].set_value(self.old_WLvar)
                        if self.old_POWERvar in keys: self["POWER var"].set_value(self.old_POWERvar)
                        if self.old_BGvar in keys: self["BG var"].set_value(self.old_BGvar)
                    case _: raise Exception("File type invalid")

        # --- Compile action ---
        @pzp.action.define(self, 'Compile', visible=True)
        def compile(self):
            # Load arrays based on datatype
            match self["datatype"].value:
                case "ds":
                    self.spectra = self.dat.raw
                    self["Wavelength"].set_value(self.dat.axis(self["WL var"].value))
                    self["Power"].set_value(self.dat.axis(self["POWER var"].value))
                    self['Background'].set_value(self.dat.metadata.get(self["BG var"].value))
                    self["Spectrum slider"].input.input.setMaximum(self.dat.axis(self["POWER var"].value).size - 1)
                case "mat":
                    self.spectra = self.dat.get(self["DATA var"].value)
                    self["Wavelength"].set_value(self.dat.get(self["WL var"].value).reshape(-1))
                    self["Power"].set_value(self.dat.get(self["POWER var"].value).reshape(-1))
                    self['Background'].set_value(self.dat.get(self["BG var"].value).reshape(-1))
                    self["Spectrum slider"].input.input.setMaximum(self.dat.get(self["POWER var"].value).size - 1)
                case _: raise Exception("File type invalid")

            # Background subtraction if checked
            if self["Sub. BG"].value:
                self.spectra_subBG = self.spectra.astype(np.int32) - self['Background'].value[np.newaxis, ...]
            else:
                self.spectra_subBG = self.spectra

            # Sum along unused axes
            unused_axes = self.find_unused_axes(self.spectra, [self["Wavelength"].value, self["Power"].value])
            self["Spectra"].set_value(
                self.spectra_subBG.sum(axis=tuple(unused_axes)) if unused_axes else self.spectra_subBG
            )
            
            self.normalize_spectra()

    def find_unused_axes(self, DATA, used_axe_list):
        # Return axes in DATA not covered by Wavelength/Power
        used_sizes = {ax.size for ax in used_axe_list}
        return [i for i, size in enumerate(DATA.shape) if size not in used_sizes]

    def normalize_spectra(self):
        # Normalize spectra to [0,1] along axis=1 if "Normalise" checked
        if self["Normalise"].value:
            S = self["Spectra"].value
            self["Norm Spectra"].set_value((S - S.min(axis=1)[...,np.newaxis]) / (S.max(axis=1)[...,np.newaxis]-S.min(axis=1)[...,np.newaxis]))
        else:
            self["Norm Spectra"].set_value(self["Spectra"].value)

    def contourGraph(self):
        # Draw contour plot of normalized spectra
        self.figure.clear()
        ax = self.figure.add_subplot(1,1,1)
        XX, YY = np.meshgrid(self["Wavelength"].value, self["Power"].value)
        ax.contourf(XX, YY, self["Norm Spectra"].value, levels=50)
        ax.set_xlabel("Wavelength")
        ax.set_ylabel("Power")
        ax.set_title("Norm. intensity" if self["Normalise"].value else "Intensity")
        self.figure.tight_layout()
        self.canvas.draw()

    def custom_layout(self):
        # Custom layout: Matplotlib figure + toolbar + PyQtGraph plots
        layout = QtWidgets.QGridLayout()

        # --- Matplotlib ---
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas)
        layout.addWidget(self.toolbar, 0, 0, 1, 2)
        layout.addWidget(self.canvas, 1, 0, 1, 2)

        # --- PyQtGraph ---
        self.pw = pg.GraphicsLayoutWidget()
        self.pw.ci.layout.setColumnStretchFactor(1, 1)
        layout.addWidget(self.pw, 2, 0, 1, 1)

        max_plot = self.pw.addPlot(0,0)
        max_plot.showGrid(True, True)
        max_plot.setLabel('left', 'Max. counts')
        max_plot.setLabel('bottom', 'Power')
        max_line = max_plot.plot([0],[0])
        
        spectrum_plot = self.pw.addPlot(0,1)
        spectrum_plot.showGrid(True, True)
        spectrum_plot.setLabel('left', 'Intensity')
        spectrum_plot.setLabel('bottom', 'Wavelength')
        slide_spectrum = spectrum_plot.plot([0],[0])

        # --- Update helpers ---
        def draw_max_line(): max_line.setData(self["Power"].value, self["Spectra"].value.sum(axis=1))
        def draw_slice_spectrum(): slide_spectrum.setData(self["Wavelength"].value, self["Norm Spectra"].value[self["Spectrum slider"].value,:])
        def update_plots(): self.contourGraph(); draw_max_line(); draw_slice_spectrum()
        def update_norm(): self.normalize_spectra(); update_plots()
        def update_bgsub(): self.actions["Compile"]()
        def update_log(): max_plot.setLogMode(self["Log scale"].value, self["Log scale"].value)
        def update_spectrum(): draw_slice_spectrum()

        # Connect param changes to plot updates
        self.actions["Compile"].called.connect(update_plots)
        self["Normalise"].changed.connect(update_norm)
        self["Sub. BG"].changed.connect(update_bgsub)
        self["Log scale"].changed.connect(update_log)
        self["Spectrum slider"].changed.connect(update_spectrum)
        
        return layout

if __name__ == "__main__":
    app = pzp.QApp([])
    puzzle = pzp.Puzzle(app, "LL viewer", debug=False)
    puzzle.add_piece("ll_viewer", Piece(puzzle), 0, 0)
    puzzle.show()
    app.exec()
