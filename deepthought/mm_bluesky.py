import time
from collections import OrderedDict 
from ophyd.status import Status
from ophyd import Device
from ophyd import Component as Cpt

class ReadableDevice:
    name = None
    parent = None

    def read(self):
        return OrderedDict()

    def describe(self):
        return OrderedDict()
    
    def trigger(self):
        status = Status(obj=self, timeout=5)
        status.set_finished()
        return status

    def read_configuration(self):
        return {}
    
    def describe_configuration(self):
        return {}
    
    hints = {}

    def configure(self, *args, **kwargs):
        pass

    def stage(self):
        pass

    def unstage(self):
        pass

    def subscribe(self, function):
        pass
    
    def clear_sub(self, function):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def add_callback(self):
        pass

class SettableDevice(ReadableDevice):
    def stop(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass
    
    position = None

class Focus(SettableDevice):
    name = "z"

    def __init__(self, mmc):
        self.mmc = mmc
        self.mmc_device_name = "Z"
        self.position = self.mmc.getPosition()

    def trigger(self):
        status = Status(obj=self, timeout=5)
        # status.add_callback(self.callback)
        self.mmc.waitForDevice(self.mmc_device_name)
        status.set_finished()
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

        self.mmc.setPosition(float(value))
        self.mmc.waitForDevice(self.mmc_device_name)
        self.position = self.mmc.getPosition()

        status.set_finished()
        return status

    def callback(self):
        print(f"moved z to: {self.mmc.getPosition()}")

class Microscope(Device):
    pass

class Camera(SettableDevice):
    def __init__(self, mmc):
        self.mmc = mmc
        self.mmc_device_name = "Camera"
        self.root = Microscope(name="scope")

    def trigger(self):
        status = Status(obj=self, timeout=5)
        # status.add_callback(self.callback)
        self.mmc.waitForDevice(self.mmc_device_name)
        status.set_finished()
        return status

    def read(self):
        data = OrderedDict()
        t = time.time()
        self.mmc.snapImage()
        self.img = self.mmc.getImage()
        data['img'] = {'value': self.img, 'timestamp': t}
        return data                          

    def describe(self):
        data = OrderedDict()
        data['camera'] = {'source': "cam-label", 
                     'dtype': "array",
                     'shape' : [512, 512]}
        return data                          

    def callback(self):
        try:
            print(f"data: {self.img}")
        except AttributeError:
            pass

    name = "cam"
    # parent = Microscope()
    # root = Microscope()

    # def stage(self):
    #     pass

    # def unstage(self):
    #     pass
    
    # def pause(self):
    #     pass

    # def resume(self):
    #     pass