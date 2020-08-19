"""MMCore hardware abstraction layer access as RPC"""
import time
import os
from configs import config
import pymmcore
import rpyc
from comms import server
from collections import OrderedDict 

mm_dir = config["mm_dir"]
config_path = config["mm_config"]
working_dir = os.getcwd()

def create_mmc_obj():
    print("creating mmc")
    mmc = pymmcore.CMMCore()
    mmc.setDeviceAdapterSearchPaths([mm_dir])
    mmc.loadSystemConfiguration(config_path)
    return mmc

def unload():
    print("unloading")
    mmc.reset()

os.chdir(mm_dir)
mmc = create_mmc_obj()
os.chdir(working_dir)

class Microscope(rpyc.Service):
    def on_connect(self, conn):
        print(f"client connected")
        self.mmc = mmc 

    def on_disconnect(self, conn):
        print(f"client disconnected")


if __name__ == "__main__":
    s = server(Microscope, **config["mm_server"])
    s.start()
    unload()