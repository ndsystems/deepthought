import time
from collections import OrderedDict 
from ophyd.status import Status
from ophyd import Device
from ophyd import Component as Cpt
import numpy as np

class DummyMMC:
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

class Microscope(Device):
    pass

class Focus(SettableDevice):
    name = "z"

    def __init__(self, mmc):
        self.mmc = mmc
        self.mmc_device_name = "Z"
        self.position = self.mmc.getPosition()

    def trigger(self):
        """
        Trigger the device.

        This does not block for triggering to complete. It promptly returns a
        Status object which can be used to detect completion.

        >>> st = my_instance.trigger()

        You can block for completion of triggering (sync).
        >>> st.wait()

        Or register a function to be called upon completion and then continue
        to run other code (async). The function f will be called like f(st)
        from another thread.
        >>> st.add_callback(f)
        """
        status = Status(obj=self, timeout=5)

        def wait():
            "This will be run on a thread."
            try:
                self.mmc.waitForDevice(self.mmc_device_name)
            except Exception as exc:
                status.set_exception(exc)
            else:
                status.set_finished()

        # Kick of a thread that will eventually mark the status as done...
        threading.Thread(target=wait).start()
        # ...and immediately return the status.
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


class Camera(SettableDevice):
    def __init__(self, mmc):
        self.mmc = mmc
        self.mmc_device_name = "Camera"
        self.root = Microscope(name="scope")

    def trigger(self):
        status = Status(obj=self, timeout=5)
        self.mmc.waitForDevice(self.mmc_device_name)
        status.set_finished()
        return status

    def read(self):
        data = OrderedDict()
        
        t = time.time()
        self.mmc.snapImage()
        self.img = self.mmc.getImage()
        self.img = np.asarray(self.img)

        data['camera'] = {'value': self.img, 'timestamp': t}
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

