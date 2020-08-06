import time
from ophyd.status import Status
from collections import OrderedDict 

class ReadableDevice:
    name = None
    parent = None

    def read(self):
        return OrderedDict()

    def describe(self):
        return OrderedDict()
    
    def trigger(self):
        pass

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
    def stop(self):
        pass

    def set(self, *args, **kwargs):
        pass
    
    position = None

class Focus(SettableDevice):
    name = "z"
    
    def __init__(self, mmc):
        self.mmc = mmc
        self.position = self.mmc.getPosition()

    def stop(self, *args, **kwargs):
        pass
    
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

    def trigger(self):
        status = Status(obj=self, timeout=5)
        status.set_finished()
        return status

 
    def set(self, value):
        status = Status(obj=self, timeout=5)
        self.mmc.setPosition(float(value))
        self.position = self.mmc.getPosition()
        status.add_callback(self.callback)
        status.set_finished()
        return status

    def callback(self):
        print(f"moved z to: {self.mmc.getPosition()}")

class Camera(SettableDevice):
    name = "camera"
    
    def __init__(self, mmc):
        self.mmc = mmc
        self.position = self.mmc.getPosition()
