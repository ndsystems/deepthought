from microscope import Microscope, ChannelConfig, RE
# make a grid for scan
import napari
import numpy as np
import matplotlib.pyplot as plt
from devices import MMCoreInterface
from optimization import shannon_dct

tritc = ChannelConfig("TRITC")
tritc.exposure = 500
tritc.model = {"kind": "nuclei",
                "diameter": 100}
    
cy5 = ChannelConfig("Cy5")
cy5.exposure = 1000
cy5.model = {"kind": "nuclei",
                "diameter": 100}

dapi = ChannelConfig("DAPI")
dapi.exposure = 30
dapi.model = {"kind": "nuclei",
                "diameter": 100}

fitc = ChannelConfig("FITC")
fitc.exposure = 1000
fitc.model = {"kind": "nuclei",
                "diameter": 100}



bf = ChannelConfig("BF")
bf.exposure = "auto"
bf.model = {"kind": "cyto",
                "diameter": 150}

def snap_image(mmc):
    mmc.snapImage()
    img = mmc.getImage()
    img = np.array(img)
    napari.view_image(img)

v = napari.Viewer()
layer = v.add_image(np.random.randint(0, 4095, (2048, 2048)))

def napari_viewer(event, document):
    if event == "event":
        if "image" in document["data"]:
            img = document["data"]["image"]
            try:
                layer.data = img
            except:
                pass


def per_step_xy(image):
    img  = image

if __name__ == "__main__":
    """    # experiment with anisotropy
    
    # step 1 - map the sample with eva green
    # step 2 - identify coordinates to image
    # step 3 - align map_eg to map_bs
    # step 4 - timelapse objects of interest
    # 
    """    
    
    scopes = MMCoreInterface()
    scopes.add("10.10.1.35", "bright_star")
    scopes.add("10.10.1.57", "eva_green")
    
    m = Microscope(mmc=scopes["bright_star"])
    # m.mmc.setXYPosition(0, 0)
    
    plan = m.scan_grid(channels=[fitc, bf], per_step_xy=per_step_xy)

    RE.subscribe(napari_viewer)

    uid, = RE(plan)

    # # snap_image(m.mmc)