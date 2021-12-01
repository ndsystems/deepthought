from microscope import Microscope
import napari
import numpy as np
from devices import MMCoreInterface
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine
from data import db
from optimization import shannon_dct
from view import AlbumViewer


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


if __name__ == "__main__":
    scopes = MMCoreInterface()
    scopes.add("10.10.1.35", "bright_star")
    scopes.add("10.10.1.57", "eva_green")

    m = Microscope(mmc=scopes["bright_star"])

    plan = m.scan_an_xy_t(channels=[fitc], num=8, cycles=26, delta_t=300)

    RE = configure_RE()
    _ = RE(plan)
