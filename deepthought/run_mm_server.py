"""MMCore hardware abstraction layer access as RPC"""
import time
import os
from configs import config
import pymmcore
import rpyc
from comms import server
from collections import OrderedDict 


class Microscope(rpyc.Service):
    name = "microscope"
    parent = None

    def __init__(self):
        self._staged = False
        self.config_path = config["mm_config"]
        self.mm_dir = config["mm_dir"]
        self.working_dir = os.getcwd()

    def on_connect(self, conn):
        print(f"Hi, {conn}")
        self.stage()

    def on_disconnect(self, conn):
        print(f"Good bye, {conn}")
    
    def create_mmc_obj(self, config_path):
        self.mmc = pymmcore.CMMCore()
        self.mmc.setDeviceAdapterSearchPaths(self.mm_dir)
        self.mmc.loadSystemConfiguration(config_path)
        self._staged = True

    def stage(self):
        if not self._staged:
            os.chdir(self.mm_dir)
            self.create_mmc_obj(self.config_path)
            os.chdir(self.working_dir)

        return self.mmc

    def unstage(self):
        self.mmc.reset()
        self._staged = False

    def read(self):
        data = OrderedDict()
        data['alive'] = {'value': self._staged, 'timestamp': time.time()}
        return data                          

    def describe(self):
        data = OrderedDict()
        data['alive'] = {'source': "MMCore", 
                     'dtype': "bool",
                     'shape' : []}
        return data

    def read_configuration(self) -> OrderedDict:
        return OrderedDict()

    def describe_configuration(self) -> OrderedDict:
        return OrderedDict()



if __name__ == "__main__":
    s = server(Microscope, **config["mm_server"])
    try:
        s.start()
    except KeyboardInterrupt:
        # unstage Microscope
        # kill server
        print(s)
