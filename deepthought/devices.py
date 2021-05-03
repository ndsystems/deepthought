"""
abstraction of devices

References:

1. https://nsls-ii.github.io/ophyd/architecture.html#uniform-high-level-interface
2. https://github.com/SEBv15/GSD192-tools
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Tuple, TypeVar

import numpy as np
from ophyd.status import Status
from ophyd import Signal
from ophyd import (Component as Cpt)
from ophyd import (PseudoPositioner, PseudoSingle)
from ophyd.pseudopos import (pseudo_position_argument,
                             real_position_argument)

from skimage import io


class BaseScope:
    def __init__(self, mmc):
        self.mmc = mmc

    def device_properties(self, device):
        """get property names and values for the given device"""
        device_props = {}

        property_names = self.mmc.getDevicePropertyNames(device)

        for property_name in property_names:
            value = self.mmc.getProperty(device, property_name)
            device_props[property_name] = value

        return device_props

    def properties(self):
        """get property names and values for all loaded devices in scope"""
        all_device_props = {}

        list_of_devices = self.mmc.getLoadedDevices()

        for device in list_of_devices:
            device_props = self.device_properties(device)
            all_device_props[device] = device_props

        return all_device_props


class pE4000(BaseScope):
    __current_led = None
    __channel = None
    __intensity_label = None

    def set_led(self, value):
        led_channels = {
            "A": [365, 385, 405, 435],
            "B": [460, 470, 490, 500],
            "C": [525, 550, 580, 595],
            "D": [635, 660, 740, 770],
        }

        for channel, led_set in led_channels.items():
            if value in led_set:
                self.__current_led = value
                self.__channel = "Channel" + channel
                self.__intensity_label = "Intensity" + channel

        self.mmc.setProperty("pE4000", self.__channel, self.__current_led)
        return self.__current_led

    def set_intensity(self, value):
        self.mmc.setProperty("pE4000", self.__intensity_label, value)
        return value


class Illumination(pE4000):
    def __init__(self):
        self.led = 490
        self.led_intensity = 0
        super(Illumination, self).__init__(self)

    @property
    def led(self):
        return self.__led

    @led.setter
    def led(self, choice):
        self.__led = self.set_led(choice)

    @property
    def led_intensity(self):
        return self.__led_intensity

    @led_intensity.setter
    def led_intensity(self, choice):
        self.__led_intensity = self.set_intensity(choice)


def random_crop(image, size=512):
    """generate a random crop of the image for the given size"""
    x, y = image.shape
    random_x = np.random.randint(0, int(x/2))
    random_y = np.random.randint(0, int(y/2))
    cropped_image = image[random_x:random_x+size, random_y:random_y+size]
    return cropped_image


def frame_crop(image, size=512, tol=100):
    """generate a random crop of the image for the given size"""
    error = np.random.randint(0, tol)
    x, y = 150, 250
    cropped_image = image[x+error:x+size+error, y+error:y+size+error]
    return cropped_image


class SimMMC:
    """This is a simulated microscope that returns a 512x512
    image."""
    def __init__(self):
        self.pos = 0
        self.xy = [0, 0]
        self.exposure_time = 0.1
        self.data = io.imread("sim_data/DAPI.tif")

    def getCameraDevice(self):
        return "SimCamera"

    def getFocusDevice(self):
        return "SimFocus"

    def snapImage(self):
        time.sleep(self.exposure_time)
        return

    def setPosition(self, value):
        self.pos = value
        return

    def getPosition(self):
        return self.pos

    def setXYPosition(self, value):
        self.xy = value
        return
    
    def getXYPosition(self):
        return self.xy


    def waitForDevice(self, label):
        time.sleep(1)
        return

    def getImage(self):
        return frame_crop(self.data)


class Focus:
    name = "z"
    parent = None

    def __init__(self, mmc):
        self.mmc = mmc
        self.mmc_device_name = self.mmc.getFocusDevice()
        self.position = self.mmc.getPosition()

    def trigger(self):
        status = Status(obj=self, timeout=10)
        
        def wait():
            try:
                self.mmc.waitForDevice(self.mmc_device_name)
            except Exception as exc:
                status.set_exception(exc)
            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status
    
    def read(self):
        data = OrderedDict()
        data['z'] = {'value': self.mmc.getPosition(), 'timestamp': time.time()}
        return data                          

    def describe(self):
        data = OrderedDict()
        data['z'] = {'source': "MMCore", 
                     'dtype': "number",
                     'shape' : []}
        return data                          


    def set(self, value):
        status = Status(obj=self, timeout=5)
        def wait():
            try:
                self.mmc.setPosition(float(value))
                self.mmc.waitForDevice(self.mmc_device_name)
                self.position = self.mmc.getPosition()
            except Exception as exc:
                status.set_exception(exc)
            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def read_configuration(self) -> OrderedDict:
        return OrderedDict()

    def describe_configuration(self) -> OrderedDict:
        return OrderedDict()


class Camera:
    name = "camera"
    parent = None
    exposure_time = None

    def __init__(self, mmc):
        self.mmc = mmc
        self.mmc_device_name = str(self.mmc.getCameraDevice())

        self.image = None

        self._subscribers = []

    def _collection_callback(self):
        for subscriber in self._subscribers:
            threading.Thread(target=subscriber).start()

    def trigger(self):
        status = Status(obj=self, timeout=10)
        
        def wait():
            try:
                self.image_time = time.time()
                self.mmc.snapImage()
                self.mmc.waitForDevice(self.mmc_device_name)

                self.image = self.mmc.getImage()
                self.image = np.asarray(self.image)

            except Exception as exc:
                status.set_exception(exc)

            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def read(self) -> OrderedDict:
        data = OrderedDict()
        data['camera'] = {'value': self.image, 'timestamp': self.image_time}
        return data

    def describe(self):
        data = OrderedDict()
        data['camera'] = {'source': self.mmc_device_name, 
                     'dtype': 'array',
                     'shape' : self.image.shape}
        return data                                                    

    def subscribe(self, func):
        if not func in self._subscribers:
            self._subscribers.append(func)

    def describe_configuration(self) -> OrderedDict:
        return OrderedDict()

    def read_configuration(self) -> OrderedDict:
        return OrderedDict()


class XYStage:
    name = "xy"
    parent = None

    def __init__(self, mmc):
        self.mmc = mmc
        self.mmc_device_name = self.mmc.getXYStageDevice()


    def trigger(self):
            status = Status(obj=self, timeout=10)
            
            def wait():
                try:
                    self.mmc.waitForDevice(self.mmc_device_name)
                except Exception as exc:
                    status.set_exception(exc)
                else:
                    status.set_finished()

            threading.Thread(target=wait).start()
            return status

    def read(self):
        data = OrderedDict()
        data['xy'] = {'value': self.mmc.getXYPosition(), 'timestamp': time.time()}
        return data

    def describe(self):
        data = OrderedDict()
        data['xy'] = {'source': "MMCore", 
                     'dtype': "number",
                     'shape' : []}
        return data                          
                          
    
    def set(self, value):
        status = Status(obj=self, timeout=5)
        def wait():
            try:
                self.mmc.setXYPosition(*value)
                self.mmc.waitForDevice(self.mmc_device_name)
            except Exception as exc:
                status.set_exception(exc)
            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def read_configuration(self) -> OrderedDict:
        return OrderedDict()

    def describe_configuration(self) -> OrderedDict:
        return OrderedDict()


class Stage(PseudoPositioner):    
    # The pseudo positioner axes:
    px = Cpt(PseudoSingle)
    py = Cpt(PseudoSingle)    
    
    # The real (or physical) positioners:
    rxy = Cpt(XYStage, self.mmc)  # FIXME:    
    
    def __init__(self, prefix='', mmc=None, *, **kwargs):
        if mmc is None:
            raise ValueError("Must supply the 'mmc' object.")
        self.mmc = mmc        
        
        # now, tell the PseudoPositioner to construct itself
        super().__init__(prefix=prefix, **kwargs)

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        '''Run a forward (pseudo -> real) calculation'''
        return self.RealPosition(rxy=(pseudo_pos.px, pseudo_pos.py))
    @real_position_argument
    def inverse(self, real_pos):
        '''Run an inverse (real -> pseudo) calculation'''
        return self.PseudoPosition(px=real_pos.rxy[0],
                                   py=real_pos.rxy[1])
