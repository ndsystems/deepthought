from microscope import Microscope
import napari
import numpy as np
from devices import MMCoreInterface
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine
from data import db
from optimization import shannon_dct
from detection import NuclearDetector
from channels import ChannelConfig


def configure_RE():
    bec = BestEffortCallback()
    bec.disable_plots()

    RE = RunEngine({})
    RE.subscribe(bec)
    RE.subscribe(db.insert)
    return RE


def snap_image(mmc):
    mmc.snapImage()
    img = mmc.getImage()
    img = np.array(img)
    print(shannon_dct(img))
    napari.view_image(img)


dapi = ChannelConfig("DAPI")
dapi.exposure = 30
dapi.detector = NuclearDetector()
dapi.marker = "nuclear"

fitc = ChannelConfig("FITC")
fitc.exposure = 200
fitc.detect_with = dapi
fitc.marker = "g-h2ax"

txred = ChannelConfig("TxRed")
txred.exposure = 200
txred.detect_with = dapi
txred.marker = "p-chk1"


if __name__ == "__main__":
    scopes = MMCoreInterface()
    scopes.add("10.10.1.35", "bright_star")
    scopes.add("10.10.1.57", "eva_green")

    m = Microscope(mmc=scopes["bright_star"])

    plan = m.scan_xy(channels=[dapi, fitc, txred], num=2, initial_coords=[0, 0])

    RE = configure_RE()
    _ = RE(plan)
