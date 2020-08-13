"""MMCore hardware abstraction layer access as RPC"""
import os
from configs import get_default
default = get_default()

import pymmcore
import rpyc
from comms import share_object

import numpy as np
from skimage import io



class Micromanager(rpyc.Service):
    def on_connect(self, conn):
        pass

    def on_disconnect(self, conn):
        pass

    def load_microscope(self, config_path=default["mm"]["cfg_file"]):
        """initialize MMCore for the given micro-manager config file"""
        config_abspath = os.path.abspath(config_path)

        working_dir = os.getcwd()

        if os.name == 'nt':
            mm_dir = default["mm"]["win_path"]

        elif os.name == "posix":
            mm_dir = default["mm"]["linux_path"]

        os.chdir(mm_dir)

        self.mmc = pymmcore.CMMCore()
        self.mmc.setDeviceAdapterSearchPaths([mm_dir])
        self.mmc.loadSystemConfiguration(config_abspath)

        os.chdir(working_dir)
        return self.mmc


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