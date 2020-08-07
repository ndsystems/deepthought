"""MMCore hardware abstraction layer access as RPC"""
import os
from configs import get_default
import pymmcore
from comms import share_object
import rpyc

default = get_default()


class Micromanager(rpyc.Service):
    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        pass

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass

    def load_microscope(self, config_path=default["mm"]["cfg_file"]):
        """initialize MMCore for the given micro-manager config file"""
        config_abspath = os.path.abspath(config_path)

        # store the current working dir, so that we can change it back after
        # device adapters are pointed to the micromanager directory
        # changing the working directory to mm_dir is necessary for pymmcore
        # to find the device adapters (stored in mm_dir) correctly
        working_dir = os.getcwd()

        if os.name == 'nt':  # check if windows
            # ah! the microscope computer
            mm_dir = default["mm"]["win_path"]

        elif os.name == "posix":
            # the dev's linux computer
            mm_dir = default["mm"]["linux_path"]

        os.chdir(mm_dir)

        mmc = pymmcore.CMMCore()
        mmc.setDeviceAdapterSearchPaths([mm_dir])
        mmc.loadSystemConfiguration(config_abspath)

        os.chdir(working_dir)
        self.exposed_mmc = mmc
        return mmc

import numpy as np
from skimage import io

def get_random_crop(img, size=300):
    """generate a random crop of the image for the given size"""

    x, y = img.shape
    random_x = np.random.randint(0, int(x/2))
    random_y = np.random.randint(0, int(y/2))
    cropped_img = img[random_x:random_x+size, random_y:random_y+size]
    return cropped_img


def get_simulated_image():
    data = io.imread("data/dapi_hela.tif")
    return get_random_crop(data)


if __name__ == "__main__":
    share_object(Micromanager)