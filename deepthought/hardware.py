"""MMCore hardware abstraction layer access as RPC"""
import os
import logging
from configs import get_default
from comms import serve_object

import pymmcore

from skimage import io
import numpy as np


default = get_default()

windows7_path = default["mm"]["win_path"]
linux_path = default["mm"]["linux_path"]


def load_microscope(config_path):
    """initialize MMCore for the given micro-manager config file"""
    config_abspath = os.path.abspath(config_path)

    # store the current working dir, so that we can change it back after
    # device adapters are pointed to the micromanager directory
    # changing the working directory to mm_dir is necessary for pymmcore
    # to find the device adapters (stored in mm_dir) correctly
    working_dir = os.getcwd()

    if os.name == 'nt':  # check if windows
        # ah! the microscope computer
        mm_dir = windows7_path
    elif os.name == "posix":
        # the dev's linux computer
        mm_dir = linux_path
    os.chdir(mm_dir)

    mmc = pymmcore.CMMCore()
    mmc.setDeviceAdapterSearchPaths([mm_dir])
    mmc.loadSystemConfiguration(config_abspath)

    os.chdir(working_dir)

    return mmc


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
    logging.basicConfig(format='%(asctime)s - %(message)s',
                        level=logging.DEBUG)

    config_file = default["mm"]["cfg_file"]

    hostname = default["mcu_server"]["hostname"]
    port = int(default["mcu_server"]["port"])

    mmc = load_microscope(config_file)

    server = serve_object(mmc, f"tcp://{hostname}:{port}")

    try:
        server.run()
    except:
        mmc.reset()
