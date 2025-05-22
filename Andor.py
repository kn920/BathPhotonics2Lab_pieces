import puzzlepiece as pzp
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
from PIL import Image
import datasets as ds
import datetime

class Settings(pzp.piece.Popup):
    def define_params(self):
        self.add_child_params(["vs_speed", "amp_mode", "input_port", "slit_width", "counts", "max_counts", "sub_background", "start_acquisition"])
        
        # Reload dropdown lists when Settings popup opened
        def relaod_dropdowns():    
            try:
                if not self.puzzle.debug:
                    self["amp_mode"].input.addItems([str(x) for x in self.cam.get_all_amp_modes()])
                    self["vs_speed"].input.addItems([str(x) for x in self.cam.get_all_vsspeeds()])
                    self.params["input_port"].input.addItems(["side"])
                    # self.params["output_port"].input.addItems(["direct", "side"])
                else:                                    
                    A = [(1,1,1), (2,2,2), (3,3,3)]
                    self["amp_mode"].input.addItems([str(x) for x in A])
                    self["vs_speed"].input.addItems([str(x) for x in A])
                    self.params["input_port"].input.addItems(["side"])
                    # self.params["output_port"].input.addItems(["direct", "side"])
            except:
                ...

            self["amp_mode"].get_value()
            self["vs_speed"].get_value()
            self["input_port"].get_value()
            self["slit_width"].get_value()
            # self["output_port"].get_value()
            
        relaod_dropdowns()

        return super().define_params()
    
    def define_actions(self):
        self.add_child_actions(["Take background", "ROI", "Export device info"])
        return super().define_actions()

class Base(pzp.Piece):
    def __init__(self, puzzle):
        # Move the custom_layout to the right of the generated inputs
        super().__init__(puzzle, custom_horizontal=True)
        # self.image will store the image the camera takes
        self.image = [0]
        self.params["sub_background"].set_value(False)

        # import pylablib as pll
        # from pylablib.devices import Andor

        # pll.par["devices/dlls/andor_sdk2"] = "C:/Program Files/Andor SOLIS"
        # self.imports = Andor      

    def define_params(self):
    
        # List and select device indices
        @pzp.param.dropdown(self, "device_index", "")
        def device_idx(self):
            return None
        
        @device_idx.set_getter(self)
        def device_idx(self):
            if self.puzzle.debug:
                self["device_index"].input.clear()
                self["device_index"].input.addItems(['0'])
                return self.params['device_index'].value
            
            self.imports.Shamrock.restart_lib()
            self["device_index"].input.clear()
            self["device_index"].input.addItems([str(x) for x in np.arange(self.imports.get_cameras_number_SDK2()+1)])
            return self.params['device_index'].value

        # Connect to device
        @pzp.param.checkbox(self, "connected", 0)
        def connect(self, value):
            if self.puzzle.debug:
                A = [(1,1,1), (2,2,2), (3,3,3)]
                self["amp_mode"].input.clear()
                self["amp_mode"].input.addItems([str(x) for x in A])
                self["vs_speed"].input.clear()
                self["vs_speed"].input.addItems([str(x) for x in A])

                B1 = np.arange(4)+1
                B2 = ["Grating A Grating A Grating A Grating A", "Grating B", "Grating C", "Grating D"]
                self["grating"].input.clear()
                for i in B1:
                        self["grating"].input.addItem(f"{i:02d} - {B2[i-1]}")

                self.params["start_acquisition"].set_value(False)

                self.params["input_port"].input.addItems(["side"])
                # self.params["output_port"].input.addItems(["direct", "side"])

                self.params["slit_width"].set_value(8)

                return value
            
            # Check if we're currently connected by checking what the state of the checkbox was
            current_value = self.params['connected'].value
            if value and not current_value:
                try:
                    self.cam = self.imports.AndorSDK2Camera(idx=int(self.params['device_index'].value), temperature=-70, fan_mode="full")
                    self.spec = self.imports.ShamrockSpectrograph()

                    # Initialise camera default amp mode
                    self.cam.init_amp_mode()
                    self["amp_mode"].input.clear()
                    self["amp_mode"].input.addItems([str(x) for x in self.cam.get_all_amp_modes()])
                    self["vs_speed"].input.clear()
                    self["vs_speed"].input.addItems([str(x) for x in self.cam.get_all_vsspeeds()])
                    self["grating"].input.clear()
                    for i in np.arange(self.spec.get_gratings_number())+1:
                        self["grating"].input.addItem(f"{i:02d} - {self.spec.get_grating_info(i)}")

                    self.params["input_port"].input.addItems(["side"])
                    # self.params["output_port"].input.addItems(["side", "direct"])

                    # Set cooler on
                    self.cam.set_cooler(on=True)

                    # Set acquisition mode to Single scan
                    self.cam.set_acquisition_mode("single")

                    # Set readout mode to Image
                    self.cam.set_read_mode("image")

                    # Set shutter state to Auto
                    self.cam.setup_shutter('auto')

                    # # Set trigger mode to Software mode
                    # self.cam.set_trigger_mode('software')

                    # Set start_acquisition param
                    self.params["start_acquisition"].set_value(False)


                    return 1
                except Exception as e:
                    self.dispose()
                    raise e
                
            elif current_value:
                # Disconnect
                if self._ensure_connected(capture_exception=True):
                    self.dispose()
                return 0
    
        # Getter for camera temperature status
        @pzp.readout.define(self, "temp_status")
        @self._ensure_connected
        def fan(self):
            if not self.puzzle.debug:
                status = self.cam.get_temperature_status()
            else:
                status = "stabilized"
            if status != "stabilized":
                self.params["temp_status"].input.setStyleSheet("background-color: yellow")
            else:
                self.params["temp_status"].input.setStyleSheet("background-color: #f3f3f3") 
            return status

        # Set exposure time
        @pzp.param.spinbox(self, "exposure", 100.)
        @self._ensure_connected
        def exposure(self, value):
            if self.puzzle.debug:
                return value
            # If we're connected and not in debug mode, set the exposure
            if self.params['start_acquisition'].get_value() == True:
                self.params['start_acquisition'].set_value(False)
            self.cam.set_exposure(value*1e-6)

        @exposure.set_getter(self)
        @self._ensure_connected
        def exposure(self):
            if self.puzzle.debug:
                return self.params['exposure'].value
            # If we're connected and not in debug mode, return the exposure from the camera
            return self.cam.get_exposure()*1e6

        # Set amp mode
        @pzp.param.dropdown(self, "amp_mode", "", visible=False)
        def amp_mode(self):
            return None

        @amp_mode.set_getter(self)
        @self._ensure_connected
        def amp_mode(self):
            if self.puzzle.debug:
                return self.params['amp_mode'].value
            amp_mode_fun = self.cam.get_amp_mode()
            return [amp_mode_fun.channel, amp_mode_fun.oamp, amp_mode_fun.hsspeed, amp_mode_fun.preamp]

        @amp_mode.set_setter(self)
        @self._ensure_connected
        def amp_mode(self, value):
            if not self.puzzle.debug:
                if self.params['start_acquisition'].get_value() == True:
                    self.params['start_acquisition'].set_value(False)
                self.cam.set_amp_mode(self.params["amp_mode"].value)
            return value

        # Set VS speed mode (vertical shift speed)
        @pzp.param.dropdown(self, "vs_speed", "", visible=False)
        def vs_speed(self):
            return None

        @vs_speed.set_getter(self)
        @self._ensure_connected
        def vs_speed(self):
            if self.puzzle.debug:
                return self.params['vs_speed'].value
            return self.cam.get_max_vsspeed()

        @vs_speed.set_setter(self)
        @self._ensure_connected
        def vs_speed(self, value):
            if not self.puzzle.debug:
                if self.params['start_acquisition'].get_value() == True:
                    self.params['start_acquisition'].set_value(False)
                self.cam.set_vsspeed(self.params["vs_speed"].value)
            return value

        # Setup ROI
        @pzp.param.array(self, 'roi', False)
        def roi(self):
            if self.params['roi'].value is None:
                return [0,1439,0,1079]
            elif not self.puzzle.debug and self.params["connected"].value:
                return self.cam.get_roi()[:4]
            else:
                return self.params['roi'].value
            
        @roi.set_setter(self)
        @self._ensure_connected
        def roi(self, value):
            if not self.puzzle.debug:
                # if self.params['start_acquisition'].get_value() == True:
                #     self.params['start_acquisition'].set_value(False)
                self.cam.set_roi(*value)
            self.params["sub_background"].set_value(False)
            return value

        @pzp.param.checkbox(self, "start_acquisition", 0, visible=False)
        @self._ensure_connected
        def start_acquisition(self, value):
            if self.puzzle.debug:
                return value
            
            current_value = self.params['start_acquisition'].value
            if value and not current_value:
                # start acquisition
                self.cam.start_acquisition()
                return 1
            elif current_value:
                # stop acquisition
                self.cam.stop_acquisition()
                return 0
            

        # Image getter
        @pzp.param.array(self, 'image')
        @self._ensure_connected
        # @self._ensure_temp_settled
        def get_image(self):
            if self.puzzle.debug:
                # If we're in debug mode, we just return random noise
                dummy_imgsize = self.params["roi"].get_value()
                image = np.random.random((dummy_imgsize[3]-dummy_imgsize[2]+1, dummy_imgsize[1]-dummy_imgsize[0]+1))*1024
            else:
                # if self.params['start_acquisition'].get_value() == False:
                #     self.params['start_acquisition'].set_value(True)

                # cam.snap handled all the acquisition start, wait, and stop 
                image = self.cam.snap()
                if image is None:
                    raise Exception('Acquisition did not complete within the timeout...')
            if self.params['sub_background'].get_value():
                image -= self.params['background'].get_value()
            return image

        # Toggle background subtraction
        @pzp.param.checkbox(self, 'sub_background', False, visible=False)
        def sub_background(self, value):
            if value:
                self._ensure_background_exist()
            return value
        
        @sub_background.set_getter(self)
        def sub_background(self):
            return self.params["sub_background"].value
        
        pzp.param.array(self, 'background', False)(None)

        # Readout for total counts
        @pzp.param.readout(self, 'counts', False)
        def get_counts(self):
            image = self.params['image'].get_value()
            return np.sum(image)
        
        # Readout for max counts
        @pzp.param.readout(self, 'max_counts', False)
        def get_counts(self):
            image = self.params['image'].get_value()
            return np.amax(image)
        
        # set grating
        @pzp.param.dropdown(self, "grating", "")
        def grating(self):
            return None
        
        @grating.set_getter(self)
        @self._ensure_connected
        def grating(self):
            if self.puzzle.debug:
                return self.params['grating'].value
            grat_idx = self.spec.get_grating()
            grat_info = self.spec.get_grating_info(grat_idx)
            return f"{grat_idx:02d} - {grat_info}"

        @grating.set_setter(self)
        @self._ensure_connected
        def grating(self, value:str):
            if not self.puzzle.debug:
                if self.params['start_acquisition'].get_value() == True:
                    self.params['start_acquisition'].set_value(False)
                grat_idx = int(value.split(" - ")[0])
                self.spec.set_grating(grat_idx)
            return value

        # Set centre wavelength
        @pzp.param.spinbox(self, "centre", 0.0)
        def centre(self, value):
            if self.puzzle.debug:
                return value
            # If we're connected and not in debug mode, set the wavelength
            if self.params['start_acquisition'].get_value() == True:
                self.params['start_acquisition'].set_value(False)
            if value == 0:
                self.spec.goto_zero_order()
            else:
                self.spec.set_wavelength(value*1e-9)

        @centre.set_getter(self)
        @self._ensure_connected
        def centre(self):
            if self.puzzle.debug:
                return self.params['centre'].value
            # If we're connected and not in debug mode, return the wavelength from the spec
            return self.spec.get_wavelength()*1e9

        # Get wavelength calibration
        @pzp.param.array(self, 'wls', True)
        def wls(self):
            roi = self.params["roi"].get_value()
            if not self.puzzle.debug:
                try:
                    self.spec.setup_pixels_from_camera(self.cam)
                    return self.spec.get_calibration()[roi[0]:roi[1]]*1e9
                except:
                    return np.linspace(1, 100, roi[1]-roi[0])
            # return np.linspace(roi[0], roi[1], (roi[1]-roi[0]+1))*3
            return np.linspace(300, 700, roi[1]-roi[0]+1)


        # Set input port
        @pzp.param.dropdown(self, "input_port", "", visible=False)
        def input_port(self):
            return None

        @input_port.set_getter(self)
        @self._ensure_connected
        def input_port(self):
            if self.puzzle.debug:
                return self.params['input_port'].value
            # return self.spec.get_flipper_port(1)
            return "side"

        @input_port.set_setter(self)
        @self._ensure_connected
        def input_port(self, value):
            if not self.puzzle.debug:
                self.spec.set_flipper_port(1, self.params["input_port"].value)
            return value

        # Set input slit width
        @pzp.param.spinbox(self, "slit_width", 8.0, visible=False)
        @self._ensure_connected
        def slit_width(self, value):
            if self.puzzle.debug:
                return value
            self.spec.set_slit_width("input_"+self.params["input_port"].value, value*1e-6)

        @slit_width.set_getter(self)
        @self._ensure_connected
        def slit_width(self):
            if self.puzzle.debug:
                return self.params['slit_width'].value
            # If we're connected and not in debug mode, return the input slit width from the spec
            return self.spec.get_slit_width("input_"+self.params["input_port"].value) * 1e6

        # # Set output port
        # @pzp.param.dropdown(self, "output_port", "", visible=False)
        # def output_port(self):
        #     return None

        # @output_port.set_getter(self)
        # @self._ensure_connected
        # def output_port(self):
        #     if self.puzzle.debug:
        #         return self.params['output_port'].value
        #     return self.spec.get_flipper_port(2)

        # @output_port.set_setter(self)
        # @self._ensure_connected
        # def output_port(self, value):
        #     if not self.puzzle.debug:
        #         self.spec.set_flipper_port(2, 'output_'+self.params["output_port"].value)
        #     return value

    def define_actions(self):
        @pzp.action.define(self, "ROI", visible=False)
        def roi(self):
            self.open_popup(ROI_Popup)

        @pzp.action.define(self, "Reset ROI", visible=False)
        @self._ensure_connected
        def reset_roi(self):
            if not self.puzzle.debug:
                roi_limits = self.cam.get_roi_limits()
                # Issue here
                self.params['roi'].set_value([0, int(roi_limits[0].max), 0, int(roi_limits[1].max)])
                self.params['roi'].set_value([int(roi_limits[0].max), int(roi_limits[1].max)])
            else:
                self.params['roi'].set_value([1080, 1440])

        @pzp.action.define(self, "Save image")
        def save_image(self, filename=None):
            image = self.params['image'].value
            if image is None:
                image = self.params['image'].get_value()

            if filename is None:
                filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self.puzzle, 'Save file as...', 
                    '.', "Image files (*.png)")
            
            Image.fromarray((image // 4).astype(np.uint8)).save(filename)

        @pzp.action.define(self, "Take background", visible=False)
        def take_background(self):
            self.params['sub_background'].set_value(False)
            background = self.params['image'].get_value()
            self.params['background'].set_value(background)
            self.params['sub_background'].set_value(True)

        @pzp.action.define(self, "Settings")
        @self._ensure_connected
        def settings(self):
            self.open_popup(Settings, "More settings")

        @pzp.action.define(self, "Export device info", visible=False)
        def export_device_info(self, filename=None):
            info_dict = None
            if not self.puzzle.debug:
                info_dict = self.spec.get_full_info(include="all")
            if info_dict is None:
                info_dict = {'foo': [1,2], 'bar':[3,4]}

            if filename is None:
                filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self.puzzle, 'Save file as...', 
                    '.', "text file (*.txt)")
            
            # create list of strings
            info_strings = [ f'{key} : {info_dict[key]}' for key in info_dict ]

            # write string one by one adding newline
            with open(filename, 'w') as my_file:
                [my_file.write(f'{st}\n') for st in info_strings]

        @pzp.action.define(self, "Save data")
        def save_data(self):

            filename = self.params["filename"].value
            if filename == "":
                filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self.puzzle, 'Save file as...', 
                    '.', "dataset file (*.ds)")
            image = self.params["image"].value
            print(image.shape)
            dat = ds.dataset(image, y_pixel=np.arange(image.shape[0]), wls=self.params["wls"].get_value())
            dat.metadata["background"] = self.params["background"].get_value()
            dat.metadata["exposure"] = self.params["exposure"].get_value()
            dat.metadata["grating"] = self.params["grating"].value
            dat.metadata["amp_mode"] = self.params["amp_mode"].value
            dat.metadata["vs_speed"] = self.params["vs_speed"].value
            dat.metadata["slit_width"] = self.params["slit_width"].get_value()
            dat.metadata["timestamp"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            dat.save(filename, 2)
            
            # For "filename" textbox not visible
            self.params["filename"].set_value = ""

    # Ensure devices are connected
    @pzp.piece.ensurer        
    def _ensure_connected(self):
        if not self.puzzle.debug and not hasattr(self, 'cam'):
            raise Exception("Camera not connected")
        if not self.puzzle.debug and not hasattr(self, 'spec'):
            raise Exception("Spectrometer not connected")
        
    # Ensure spectrometer temperature is settled
    @pzp.piece.ensurer        
    def _ensure_temp_settled(self):
        if not self.puzzle.debug and not self.params["temp_status"] == "stabilized":
            raise Exception("Spectrometer temperature not stabilised")   
 
    # Ensure background is taken
    @pzp.piece.ensurer        
    def _ensure_background_exist(self):
        if self.puzzle.debug and self.params["background"].get_value() is None:
            raise Exception("Background is not taken") 
        roi = self.params["roi"].get_value()
        if self.params["background"].get_value().shape != (roi[3] - roi[2] + 1, roi[1] - roi[0] + 1):
            raise Exception("Background ROI not match") 

    def setup(self):
        import pylablib as pll
        from pylablib.devices import Andor

        pll.par["devices/dlls/andor_sdk2"] = "C:/Program Files/Andor SOLIS"
        self.imports = Andor

    def dispose(self):
        # This function 'disposes' of the camera, effectively disconnecting us
        if hasattr(self, 'cam'):
            self.cam.close()
            self.spec.close()
            del self.cam
            del self.spec

    # Disconnect the camera when window close
    def handle_close(self, event):
        self.dispose()

class ROI_Popup(pzp.piece.Popup):
    def define_actions(self):
        @pzp.action.define(self, "set_roi_from_camera", visible=False)
        def set_roi_from_camera(self):
            camera_roi = self.parent_piece.params['roi'].get_value()
            self.roi_item.setPos(camera_roi[[0, 2]])
            self.roi_item.setSize([camera_roi[1]-camera_roi[0]+1, camera_roi[3]-camera_roi[2]+1])

        @pzp.action.define(self, "Capture ref")
        def capture_reference(self):
            if not self.puzzle.debug:
                original_roi = self.parent_piece.params['roi'].get_value()
                self.parent_piece.actions['Reset ROI']()
            image = self.parent_piece.params['image'].get_value()
            print(image.shape)
            self._rows, self._cols = image.shape
            self.imgw.setImage(image[:,::-1])
            if not self.puzzle.debug:
                self.parent_piece.params['roi'].set_value(original_roi)

        @pzp.action.define(self, "Set ROI")
        def set_roi(self):
            x1, y1 = self.roi_item.pos()
            x2, y2 = self.roi_item.size()
            x2 += x1 - 1
            y2 += y1 - 1
            x1, x2, y1, y2 = (int(np.round(x)) for x in (x1, x2, y1, y2))
            x1 = x1 if x1>0 else 0
            y1 = y1 if y1>0 else 0
            x2 = x2 if x2<self._cols-1 else self._cols-1
            y2 = y2 if y2<self._rows-1 else self._rows-1

            self.parent_piece.params["roi"].set_value([x1, x2, y1, y2])
            self.actions['set_roi_from_camera']()

        @pzp.action.define(self, "Centre")
        def centre_roi(self):
            pos, size = self.roi_item.pos(), self.roi_item.size()
            self.roi_item.setPos((self._cols/2 - size[0]/2, self._rows/2 - size[1]/2))

        @pzp.action.define(self, "Reset")
        def reset_roi(self):
            self.roi_item.setPos((0, 0))
            self.roi_item.setSize((self._cols, self._rows))

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # Make an ImageView
        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)

        plot_item = self.pw.getPlotItem()
        plot_item.setAspectLocked(True)
        plot_item.invertY(True)
        plot_item.showGrid(True, True)

        self.imgw = pg.ImageItem(border='w', axisOrder='row-major')
        plot_item.addItem(self.imgw)

        # Make a ROI
        self.roi_item = pg.ROI([0, 0], [10, 10], pen=(255, 255, 0, 200))
        self.roi_item.addScaleHandle([0.5, 1], [0.5, 0.5])
        self.roi_item.addScaleHandle([1, 0.5], [0.5, 0.5])
        self.actions['set_roi_from_camera']()
        self.actions['Capture ref']()
        self.imgw.update()
        plot_item.addItem(self.roi_item)

        return layout

class Piece(Base):
    def define_params(self):
        super().define_params()

        @pzp.param.checkbox(self, "autolevel", 0)
        def autolevel(self, value):
            image = self["image"].value
            if value and image is not None:
                self.imgw.setLevels([np.amin(image), np.amax(image)])
            else:
                self.imgw.setLevels([0, 1024])

        # Make it visible again after the textbox span issue solved
        pzp.param.text(self, "filename", "", visible=False)(None)

    # Within this function we can define any other GUI objects we want to display beyond the 
    # params and actions (which are generated by default)
    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # Add a PuzzleTimer for live view
        delay = 0.05 if not self.puzzle.debug else 0.1 # Introduce artificial delay for debug mode
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['image'].get_value, delay)
        layout.addWidget(self.timer)

        # Make an ImageView
        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)

        plot_item = self.pw.getPlotItem()
        plot_item.setAspectLocked(True)
        plot_item.invertY(True)

        # numba makes this slightly faster, uncomment if needed
        # pg.setConfigOption('useNumba', True)
        self.imgw = pg.ImageItem(border='w', axisOrder='row-major', levels=[0, 1024])
        self["autolevel"].set_value(0)
        plot_item.addItem(self.imgw)

        def update_image():
            self.imgw.setImage(self.params['image'].value, autoLevels=self["autolevel"].value)
        update_later = pzp.threads.CallLater(update_image)
        self.params['image'].changed.connect(update_later)

        layout.setStretchFactor(self.pw, 9)

        return layout
    
    def call_stop(self):
        self.timer.stop()

class LineoutPiece(Piece):
    def define_actions(self):
        super().define_actions()

        @pzp.action.define(self, 'Centre lines', QtCore.Qt.Key.Key_C)
        def centre(self):
            shape = self.params['image'].value.shape
            self._inf_line_x.setValue(shape[0]//2)
            self._inf_line_y.setValue(shape[1]//2)

    def define_params(self):
        super().define_params()

        pzp.param.spinbox(self, 'circle_r', 200, visible=False)(None)

    
    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # Add a PuzzleTimer for live view
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['image'].get_value, 0.1)
        layout.addWidget(self.timer)

        # Make the plots
        self.gl = pg.GraphicsLayoutWidget()
        layout.addWidget(self.gl)
        self.gl.ci.layout.setRowStretchFactor(0, 1)
        self.gl.ci.layout.setRowStretchFactor(1, 8)
        self.gl.ci.layout.setRowStretchFactor(2, 8)

        self.gl.ci.layout.setColumnStretchFactor(0, 5)
        self.gl.ci.layout.setColumnStretchFactor(1, 1)

        plot_main = self.gl.addPlot(1, 0)
        plot_x = self.gl.addPlot(0, 0)
        plot_x.setXLink(plot_main)
        plot_y = self.gl.addPlot(1, 1)
        plot_y.setYLink(plot_main)
        plot_fvb = self.gl.addPlot(2, 0)

        def px2wl_mapping():
            image_min = self.params["roi"].get_value()[0]
            image_max = self.params["roi"].get_value()[1] + 1
            wl_min = self.params["wls"].get_value()[0]
            wl_max = self.params["wls"].get_value()[-1]
            m = (wl_max - wl_min) / (image_max - image_min)
            c = wl_min - image_min * m
            return m ,c

        def sync_plot_fvb(vb):
            main_xrange = vb.viewRange()[0]  # [min, max] from plot_main
            m, c = px2wl_mapping()
            scaled_xrange = [x*m+c for x in main_xrange]  # Scaling
            plot_fvb.setXRange(*scaled_xrange, padding=0)

        def sync_plot_main(vb):       
                fvb_xrange = vb.viewRange()[0]  # [min, max] from plot_fvb
                m, c = px2wl_mapping()
                x0, x1 = [(x - c) / m for x in fvb_xrange]  # Scaling

                # Compute y-range to maintain aspect ratio
                vb_main = plot_main.getViewBox()
                view_rect = vb_main.viewRect()
                aspect = view_rect.width() / view_rect.height()  # current aspect

                y_center = view_rect.center().y()
                new_width = x1 - x0
                new_height = new_width / aspect
                y0 = y_center - new_height / 2
                y1 = y_center + new_height / 2

                vb_main.setRange(xRange=(x0, x1), yRange=(y0, y1), padding=0)

        plot_main.setAspectLocked(True)
        plot_main.invertY(True)
        h, w = self.params['roi'].get_value()[[1,3]]
        plot_main.setXRange(0, w)
        plot_main.setYRange(0, h)   
        plot_y.invertY(True)

        # numba makes this slightly faster, uncomment if needed
        # pg.setConfigOption('useNumba', True)
        self.imgw = pg.ImageItem(border='w', axisOrder='row-major', levels=[0, 1024])
        self["autolevel"].set_value(0)
        plot_main.addItem(self.imgw)

        self._inf_line_x = pg.InfiniteLine(0, 0, movable=True, bounds=[0, np.inf])
        self._inf_line_y = pg.InfiniteLine(0, 90, movable=True, bounds=[0, np.inf])
        self._inf_line_fvb = pg.InfiniteLine(0, 90, movable=False)
        plot_main.addItem(self._inf_line_x)
        plot_main.addItem(self._inf_line_y)
        plot_fvb.addItem(self._inf_line_fvb)

        r = self.params['circle_r'].value
        self._circle = QtWidgets.QGraphicsEllipseItem(-r, -r, r*2, r*2)  # x, y, width, height
        self._circle.setPen(pg.mkPen((255, 255, 0, 150)))
        plot_main.addItem(self._circle)

        plot_line_x = plot_x.plot([0], [0])
        plot_line_y = plot_y.plot([0], [0])
        plot_line_fvb = plot_fvb.plot([0], [0])


        def update_image():
            image_data = self.params['image'].value
            self.imgw.setImage(image_data, autoLevels=self["autolevel"].value)
            r = self.params['circle_r'].value

            roi = self.params["roi"].get_value()
            self._inf_line_x.setBounds([0, roi[3]-roi[2]])
            self._inf_line_y.setBounds([0, roi[1]-roi[0]])

            self._circle.setRect(self._inf_line_y.value()-r,
                                self._inf_line_x.value()-r,
                                r*2, r*2)
            plot_line_x.setData(image_data[int(self._inf_line_x.value())])
            i = int(self._inf_line_y.value())
            plot_line_y.setData(image_data[:, i], range(len(image_data[:, i])))
                
            plot_line_fvb.setData(self.params["wls"].get_value(), image_data.sum(axis=0))
            m, c = px2wl_mapping()
            self._inf_line_fvb.setPos([x*m+c for x in self._inf_line_y.getPos()])
             
        update_later = pzp.threads.CallLater(update_image)
        self.params['image'].changed.connect(update_later)
        self._inf_line_x.sigPositionChanged.connect(update_image)
        self._inf_line_y.sigPositionChanged.connect(update_image)
        plot_main.sigXRangeChanged.connect(sync_plot_fvb)
        plot_fvb.sigXRangeChanged.connect(sync_plot_main)

        return layout
    
    def call_stop(self):
        self.timer.stop()


if __name__ == "__main__":
    # If running this file directly, make a Puzzle, add our Piece, and display it
    app = QtWidgets.QApplication([])
    puzzle = pzp.Puzzle(app, "Lab", debug=True)
    puzzle.add_piece("Andor", LineoutPiece(puzzle), 0, 0)
    puzzle.show()
    app.exec()


