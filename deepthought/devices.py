"""
References:

1. https://nsls-ii.github.io/ophyd/architecture.html#uniform-high-level-interface
2. https://github.com/SEBv15/GSD192-tools
"""
import time
import threading
from typing import Dict, List, Any, TypeVar, Tuple


from collections import OrderedDict 
from ophyd.status import Status

import numpy as np
from skimage import io


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
