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

from ophyd import Component
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


def get_mmc():
    mmc = client(addr="10.10.1.35", port=18861).mmc
    return mmc


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

    def setCameraDevice(self, cam):
        self.cam_device = cam

    def getAllowedPropertyValues(self):
        pass


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
                     'shape': []}
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
        self.cam_name = "right_port"
        # self.configure()

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

    def set_property(self, prop, idx):
        values = self.mmc.getAllowedPropertyValues(self.cam_name, prop)
        self.mmc.setProperty(self.cam_name, prop, values[idx])
        return self.mmc.getProperty(self.cam_name, prop)

    def set_channel(self, channel):
        self.mmc.setConfig("channel", channel)
        return f"{channel}"

    def set_exposure(self, exposure_time):
        self.mmc.setExposure(exposure_time)
        return self.mmc.getExposure()

    def configure(self):
        self.mmc.setCameraDevice(self.cam_name)
        print(self.set_property("Binning", -1))
        print(self.set_property("PixelReadoutRate", 0))
        print(self.set_property("Sensitivity/DynamicRange", 0))

    def read(self) -> OrderedDict:
        data = OrderedDict()
        data['camera'] = {'value': self.image, 'timestamp': self.image_time}
        return data

    def describe(self):
        data = OrderedDict()
        data['camera'] = {'source': self.mmc_device_name,
                          'dtype': 'array',
                          'shape': self.image.shape}
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
        data['xy'] = {'value': self.mmc.getXYPosition(),
                      'timestamp': time.time()}
        return data

    def describe(self):
        data = OrderedDict()
        data['xy'] = {'source': "MMCore",
                      'dtype': "number",
                      'shape': []}
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


class SoftMMCPositioner(SignalPositionerMixin, Signal):

    _move_thread = None

    def __init__(self, *args, mmc=None, **kwargs):
        self.mmc = get_mmc()
        self.mmc_device_name = self.mmc.getXYStageDevice()

        super().__init__(*args, set_func=self._write_xy, **kwargs)

        # get the position from the controller on startup
        self._readback = np.array(self.mmc.getXYPosition())

    def _write_xy(self, value, **kwargs):
        if self._move_thread is not None:
            # The MoveStatus object defends us; this is just an additional safeguard.
            # Do not ever expect to see this warning.
            warnings.warn("Already moving.  Will not start new move.")
        st = MoveStatus(self, target=value)

        def moveXY():
            self.mmc.setXYPosition(*value)
            # ALWAYS wait for the device
            self.mmc.waitForDevice(self.mmc_device_name)

            # update the _readback attribute (which triggers other ophyd actions)
            # np.array on the netref object forces conversion to np.array
            self._readback = np.array(self.mmc.getXYPosition())

            # MUST set to None BEFORE declaring status True
            self._move_thread = None
            st.set_finished()

        self._move_thread = threading.Thread(target=moveXY)
        self._move_thread.start()
        return st


class TwoD_XY_StagePositioner(PseudoPositioner):

    # The pseudo positioner axes:
    x = Component(PseudoSingle, target_initial_position=True)
    y = Component(PseudoSingle, target_initial_position=True)

    # The real (or physical) positioners:
    # NOTE: ``mmc`` object MUST be defined`` first.
    pair = Component(SoftMMCPositioner, mmc=get_mmc())

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        """Run a forward (pseudo -> real) calculation (return pair)."""
        return self.RealPosition(pseudo_pos)

    # @real_position_argument
    def inverse(self, real_pos):
        """Run an inverse (real -> pseudo) calculation (return x & y)."""
        if len(real_pos) == 1:
            if real_pos.pair is None:
                # as called from .move()
                x, y = self.pair.mmc.getXYPosition()
            else:
                # initial call, get position from the hardware
                x, y = tuple(real_pos.pair)
        elif len(real_pos) == 2:
            # as called directly
            x, y = real_pos
        else:
            raise ValueError(
                f"Incorrect argument: {self.name}.inverse({real_pos})"
            )
        return self.PseudoPosition(x=x, y=y)
