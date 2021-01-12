"""
abstraction of devices

References:

1. https://nsls-ii.github.io/ophyd/architecture.html#uniform-high-level-interface
2. https://github.com/SEBv15/GSD192-tools
"""

import time
import threading
from typing import Dict, List, Any, TypeVar, Tuple


from collections import OrderedDict 

import numpy as np
from skimage import io

from ophyd.status import Status

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
        super(Illumination, self).__init__()

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


class SimMMC:
    """This is a simulated microscope that returns a 512x512
    image."""
    pos = 0
    xy = [0, 0]

    def snapImage(self):
        pass

    def setPosition(self, value):
        self.pos = value
    
    def getPosition(self):
        return self.pos

    def setXYPosition(self, value):
        self.xy = value
    
    def getXYPosition(self):
        return self.xy


    def waitForDevice(self, label):
        pass

    def getImage(self):
        img = self.get_simulated_image()
        return img

    def get_random_crop(self, img, size=512):
        """generate a random crop of the image for the given size"""
        x, y = img.shape
        random_x = np.random.randint(0, int(x/2))
        random_y = np.random.randint(0, int(y/2))
        cropped_img = img[random_x:random_x+size, random_y:random_y+size]
        return cropped_img

    def get_simulated_image(self):
        data = io.imread("sim_data/DAPI.tif")
        return self.get_random_crop(data)





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

    def __init__(self, mmc):
        self.mmc = mmc
        self.mmc_device_name = str(self.mmc.getCameraDevice())

        self.image = None

        self._subscribers = []

    def _collection_callback(self):
        self.total_images += 1
        
        for subscriber in self._subscribers:
            threading.Thread(target=subscriber).start()

    def trigger(self):
        status = Status(obj=self, timeout=10)
        
        def wait():
            try:
                self.img_time = time.time()
                self.mmc.snapImage()
                self.mmc.waitForDevice(self.mmc_device_name)

                self.img = self.mmc.getImage()
                self.img = np.asarray(self.img)

            except Exception as exc:
                status.set_exception(exc)

            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def read(self) -> OrderedDict:
        data = OrderedDict()
        data['camera'] = {'value': self.img, 'timestamp': self.img_time}
        return data

    def describe(self):
        data = OrderedDict()
        data['camera'] = {'source': self.mmc_device_name, 
                     'dtype': 'array',
                     'shape' : self.img.shape}
        return data                                                    

    def subscribe(self, func):
        if not func in self._subscribers:
            self._subscribers.append(func)
