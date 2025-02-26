"""Device abstractions for microscope control.

This module provides interfaces for controlling microscope hardware components
including cameras, stages, and illumination devices.

References:
1. https://nsls-ii.github.io/ophyd/architecture.html#uniform-high-level-interface
2. https://github.com/SEBv15/GSD192-tools
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Tuple, TypeVar, Optional

from ophyd import Component, Device
from ophyd import DynamicDeviceComponent as DDCpt
from ophyd import PseudoPositioner
from ophyd import PseudoSingle
from ophyd import SoftPositioner
from ophyd.pseudopos import pseudo_position_argument
from ophyd.pseudopos import real_position_argument

import numpy as np
from ophyd.status import Status
from ophyd.status import MoveStatus
from ophyd.mixins import SignalPositionerMixin
from ophyd import Signal

from skimage import io
import warnings
from comms import client
import rpyc

import socket


class MMCoreInterface:
    """Interface for managing multiple MMCore client connections."""
    
    def __init__(self) -> None:
        self.clients: Dict[str, Any] = {}
        self.named: Dict[str, Any] = {}

    def add(self, ip_addr: str, name: str) -> None:
        """Add a new MMCore client connection.
        
        Args:
            ip_addr: IP address of the MMCore server
            name: Friendly name for this connection
        """
        if ip_addr not in self.clients:
            try:
                mmc = self.connect_client(ip_addr)
                self.clients[ip_addr] = mmc
                self.named[name] = mmc
            except (ConnectionError, EOFError) as e:
                print(f"Connection failed: {e}")
            except socket.timeout:
                retry = input("Connection timed out. Try again? (y/n)\n").lower()
                if retry == "y":
                    self.add(ip_addr, name)

    def connect_client(self, addr):
        mmc = client(addr=addr, port=18861).mmc
        return mmc

    def __getitem__(self, name):
        if type(name) is int:
            index = name
            key_of_index = list(self.named.keys())[index]
            return self.named[key_of_index]
        return self.named[name]

    def __repr__(self):
        return str(self.named)

    def __iter__(self):
        return next(self.clients)


class BaseScope:
    """Base class for microscope functionality."""
    
    def __init__(self, mmc: Optional[Any] = None) -> None:
        self.mmc = mmc

    def device_properties(self, device: str) -> Dict[str, Any]:
        """Get property names and values for the given device.
        
        Args:
            device: Name of the device
            
        Returns:
            Dictionary of property names and their values
        """
        device_props = {}
        property_names = self.mmc.getDevicePropertyNames(device)
        return {
            prop_name: self.mmc.getProperty(device, prop_name)
            for prop_name in property_names
        }

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
    random_x = np.random.randint(0, int(x / 2))
    random_y = np.random.randint(0, int(y / 2))
    cropped_image = image[random_x : random_x + size, random_y : random_y + size]
    return cropped_image


def frame_crop(image, size=512, tol=100):
    """generate a random crop of the image for the given size"""
    error = np.random.randint(0, tol)
    x, y = 150, 250
    cropped_image = image[x + error : x + size + error, y + error : y + size + error]
    return cropped_image


class Focus:
    name = "z"
    parent = None

    def __init__(self, mmc=None):
        self.mmc = mmc
        self.mmc_device_name = self.mmc.getFocusDevice()

    def read(self):
        data = OrderedDict()
        data["z"] = {"value": self.mmc.getPosition(), "timestamp": time.time()}
        return data

    def describe(self):
        data = OrderedDict()
        data["z"] = {"source": "MMCore", "dtype": "number", "shape": []}
        return data

    def set(self, value):
        status = Status(obj=self, timeout=10)

        def wait():
            try:
                self.mmc.setPosition(float(value))
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


class Exposure:
    name = "exposure"
    parent = None

    def __init__(self, mmc, parent=None):
        self.mmc = mmc

    def trigger(self):
        status = Status(obj=self, timeout=10)

        def wait():
            status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def set(self, value):
        status = Status(obj=self, timeout=10)

        def wait():
            try:
                self.mmc.setExposure(value)

            except Exception as exc:
                status.set_exception(exc)
            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def read(self):
        data = OrderedDict()
        data["exposure"] = {"value": self.mmc.getExposure(), "timestamp": time.time()}
        return data

    def describe(self):
        data = OrderedDict()
        data["exposure"] = {"source": "MMCore", "dtype": "number", "shape": []}
        return data

    def read_configuration(self) -> OrderedDict:
        return OrderedDict()

    def describe_configuration(self) -> OrderedDict:
        return OrderedDict()


class TransmittedIllumination:
    name = "dia"

    def __init__(self, mmc=None, **kwargs):
        self.mmc = mmc
        self.mmc_device_name = "TransmittedIllumination 2"

    def set(self, value):
        status = Status(obj=self, timeout=10)

        def wait():
            try:
                self.mmc.setProperty("TransmittedIllumination 2", "Brightness", value)
                self.mmc.waitForDevice(self.mmc_device_name)

            except Exception as exc:
                status.set_exception(exc)
            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def read(self):
        data = OrderedDict()
        value = self.mmc.getProperty("TransmittedIllumination 2", "Brightness")
        data["dia-intensity"] = {"value": int(value), "timestamp": time.time()}
        return data

    def describe(self):
        data = OrderedDict()
        data["dia-intensity"] = {
            "source": self.mmc_device_name,
            "dtype": "number",
            "shape": [],
        }
        return data


class Camera:
    """Interface for microscope camera control."""
    
    name = "camera"
    
    def __init__(self, mmc: Optional[Any] = None, **kwargs) -> None:
        self.mmc = mmc
        self._cam_name = "left_port"  # Use single underscore for "private" attrs
        self.exposure = Exposure(self.mmc)
        self._mmc_device_name = str(self.mmc.getCameraDevice())
        self._subscribers: List[Any] = []
        self._image: Optional[np.ndarray] = None
        self._image_time: Optional[float] = None

    @property
    def image(self) -> np.ndarray:
        """Most recent captured image."""
        if self._image is None:
            raise ValueError("No image captured yet")
        return self._image

    def _collection_callback(self):
        for subscriber in self._subscribers:
            threading.Thread(target=subscriber).start()

    def trigger(self):
        status = Status(obj=self, timeout=30)

        def wait():
            try:
                self.image_time = time.time()
                self.mmc.snapImage()
                self.mmc.waitForDevice(self.mmc_device_name)

                self.image = rpyc.classic.obtain(self.mmc.getImage())

            except Exception as exc:
                status.set_exception(exc)

            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def set_property(self, prop, idx):
        values = self.mmc.getAllowedPropertyValues(self.cam_name, prop)
        self.mmc.setProperty(self.cam_name, prop, values[idx])
        self.mmc.waitForSystem()
        return self.mmc.getProperty(self.cam_name, prop)

    def configure(self):
        self.mmc.setCameraDevice(self.cam_name)
        print(self.set_property("Binning", -2))
        print(self.set_property("PixelReadoutRate", 0))
        print(self.set_property("Sensitivity/DynamicRange", 0))

    def read(self) -> OrderedDict:
        data = OrderedDict()
        data["image"] = {"value": self.image, "timestamp": self.image_time}
        return data

    def describe(self):
        data = OrderedDict()
        data["image"] = {
            "source": self.mmc_device_name,
            "dtype": "array",
            "shape": self.image.shape,
        }
        return data

    def subscribe(self, func):
        if not func in self._subscribers:
            self._subscribers.append(func)

    def describe_configuration(self) -> OrderedDict:
        return OrderedDict()

    def read_configuration(self) -> OrderedDict:
        return OrderedDict()


class AutoFocus:
    name = "zdc"
    parent = None

    def __init__(self, mmc=None, **kwargs):
        self.mmc = mmc
        self._subscribers = []
        self.mmc_device_name = self.mmc.getAutoFocusDevice()

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

    def set(self, value):
        status = Status(obj=self, timeout=10)

        def wait():
            try:
                if type(value) is bool:
                    self.mmc.enableContinuousFocus(value)
                    self.mmc.waitForDevice(self.mmc_device_name)

                elif type(value) is float:
                    self.mmc.setAutoFocusOffset(value)
                    self.mmc.waitForDevice(self.mmc_device_name)

            except Exception as exc:
                status.set_exception(exc)
            else:
                status.set_finished()

        threading.Thread(target=wait).start()

        return status

    def read(self) -> OrderedDict:
        data = OrderedDict()
        data["zdc"] = {
            "value": self.mmc.isContinuousFocusEnabled(),
            "timestamp": time.time(),
        }
        return data

    def describe(self):
        data = OrderedDict()
        data["zdc"] = {"source": self.mmc_device_name, "dtype": "boolean", "shape": []}
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

    def __init__(self, mmc=None):
        self.mmc = mmc
        self.mmc_device_name = self.mmc.getXYStageDevice()

    def read(self):
        data = OrderedDict()
        data["xy"] = {
            "value": np.array(self.mmc.getXYPosition()),
            "timestamp": time.time(),
        }
        return data

    def describe(self):
        data = OrderedDict()
        data["xy"] = {
            "source": "MMCore",
            "dtype": "array",
            "shape": [
                2,
            ],
        }
        return data

    def set(self, value):
        status = Status(obj=self, timeout=10)

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


class Channel:
    name = "channel"
    parent = None

    def __init__(self, mmc=None):
        self.config_name = "channel"
        self.mmc = mmc
        self.channels = self.mmc.getAvailableConfigs(self.config_name)

    def read(self):
        data = OrderedDict()
        self.mmc.waitForSystem()
        value = self.mmc.getCurrentConfig(self.config_name)
        data["channel"] = {"value": value, "timestamp": time.time()}
        return data

    def describe(self):
        data = OrderedDict()
        data["channel"] = {"source": "MMCore", "dtype": "string", "shape": []}
        return data

    def set(self, value):
        status = Status(obj=self, timeout=10)

        def wait():
            try:
                self.mmc.setConfig(self.config_name, value)
                self.mmc.waitForConfig(self.config_name, value)
                self.mmc.waitForSystem()

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
