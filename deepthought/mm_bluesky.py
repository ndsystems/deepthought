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
    """This is a simulated microscope"""
    pos = 0

    def snapImage(self):
        pass

    def setPosition(self, value):
        self.pos = value
    
    def getPosition(self):
        return self.pos

    def waitForDevice(self, label):
        pass

    def getImage(self):
        return np.empty(shape=(512,512))

    def get_random_crop(self, img, size=300):
        """generate a random crop of the image for the given size"""
        x, y = img.shape
        random_x = np.random.randint(0, int(x/2))
        random_y = np.random.randint(0, int(y/2))
        cropped_img = img[random_x:random_x+size, random_y:random_y+size]
        return cropped_img

    def get_simulated_image(self):
        data = io.imread("data/dapi_hela.tif")
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

        self._config = OrderedDict([
            ('exposure', {'value': 10, 'timestamp': time.time()}),
            ('gain', {'value': 1, 'timestamp': time.time()}),
            ('binning', {'value': 4, 'timestamp': time.time()}),
            ('rate', {'value': 520, 'timestamp': time.time()}),
        ])

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

    def clear_sub(self, func):
        self._subscribers.remove(func)

    def read_configuration(self) -> OrderedDict:
        return self._config.copy()

    def describe_configuration(self) -> OrderedDict:
        return OrderedDict([
            ('exposure', {'source': self.mmc_device_name, 'dtype': 'number', 'shape': []}),
            ('gain', {'source': self.mmc_device_name, 'dtype': 'number', 'shape': []}),
            ('binning', {'source': self.mmc_device_name, 'dtype': 'number', 'shape': []}),
            ('rate', {'source': self.mmc_device_name, 'dtype': 'number', 'shape': []})
        ])


    def configure(self, exposure:int=None, gain:int=None, binning:int=None, rate:int=None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        old = self.read_configuration()
        if exposure is not None:
            if not 10 <= exposure <= 5000:
                # this shouldn't be hard coded
                raise ValueError("Exposure must be between 10 - 5000 ms")
            self._config["exposure"]["value"] = exposure
            self._config["exposure"]["timestamp"] = time.time()
        
        if gain is not None:
            if gain not in [0, 1]:
                raise ValueError("Gain must be either 0 or 1")
            self._config["gain"]["value"] = gain
            self._config["gain"]["timestamp"] = time.time()
        
        if binning is not None:
            if binning not in [1, 2, 4]:
                raise ValueError("Binning is only possible for 1, 2 or 4")
            self._config["binning"]["value"] = binning
            self._config["binning"]["timestamp"] = time.time()
        
        if rate is not None:
            if rate not in [540, 240]:
                # verify these values
                raise ValueError("Read rate should be 540 or 240")
            self._config["rate"]["value"] = rate
            self._config["rate"]["timestamp"] = time.time()

        # set the values with micromanager

        return old, self.read_configuration()

    def pause(self):
        pass

    def resume(self):
        pass