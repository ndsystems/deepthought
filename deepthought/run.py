from microscope import Microscope
import napari
import numpy as np
from devices import MMCoreInterface
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine
from data import db
from optimization import shannon_dct

def configure_RE():
    bec = BestEffortCallback()
    bec.disable_plots()

    RE = RunEngine({})
    RE.subscribe(bec)
    RE.subscribe(db.insert)
    return RE


class ChannelConfig:
    def __init__(self, name="BF"):
        self.name = name
        self.exposure = None
        self.model = None

        if self.exposure is None:
            self.exposure = "auto"

    def __repr__(self):
        return str(self.name)


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
fitc.exposure = 500
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
    print(shannon_dct(img))
    napari.view_image(img)

# v = napari.Viewer()
# layer = v.add_image(np.random.randint(0, 4095, (2048, 2048)))
imgs = []
def napari_viewer(event, document):
    if event == "event":
        if "image" in document["data"]:
            img = document["data"]["image"]
            imgs.append(img)
            layer.data = np.concatenate((layer.data, img), axis=0)

if __name__ == "__main__":
    scopes = MMCoreInterface()
    scopes.add("10.10.1.35", "bright_star")
    scopes.add("10.10.1.57", "eva_green")
    
    m = Microscope(mmc=scopes["bright_star"])
    
    plan = m.scan_an_t(channels=[fitc], cycles=2, delta_t=1)

    RE = configure_RE()
    # RE.subscribe(napari_viewer)
    _ = RE(plan)
