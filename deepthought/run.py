from microscope import Microscope, ChannelConfig, RE
# make a grid for scan
import napari
import numpy as np
import matplotlib.pyplot as plt
from devices import MMCoreInterface

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


def snap_image(mmc):
    mmc.snapImage()
    img = mmc.getImage()
    img = np.array(img)
    napari.view_image(img)



if __name__ == "__main__":
    scopes = MMCoreInterface()
    scopes.add("10.10.1.35", "bright_star")
    scopes.add("10.10.1.57", "eva_green")
    
    m_1 = Microscope(mmc=scopes["bright_star"])
    m_2 = Microscope(mmc=scopes["eva_green"])


    
    
    # plan = m.scan(channel=dapi, secondary_channels=[fitc, cy5], num=5000)

    # uid, = RE(plan)
    # # snap_image(m.mmc)