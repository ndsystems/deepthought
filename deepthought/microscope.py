"""
To do:

1. configure number of cameras and camera parameters easily from user code.
2. xy, z into a position object.
    Stage.x

"""
import numpy as np
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.plans import count, spiral_square, rel_scan, list_scan
from bluesky import plan_stubs
from bluesky.simulators import summarize_plan
from configs import store_disk
from devices import Camera, Focus, TwoD_XY_StagePositioner, get_mmc, Channel
from compute import axial_length
from bluesky.callbacks.broker import post_run
from data import db
import napari
# other devices have to be added.
# to figure out where


bec = BestEffortCallback()
bec.disable_plots()

RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)

# if store_disk:
#     from bluesky.callbacks.broker import LiveTiffExporter

#     template = "output_dir/{start[scan_id]}/{event[seq_num]}.tiff"
#     live = LiveTiffExporter("camera",
#                             template=template,
#                             db=db,
#                             overwrite=True)
#     RE.subscribe(live)


def images_from_uid(uid):
    header = db[uid]
    imgs = np.stack(header.table()["camera"].to_numpy())
    return imgs


class ChannelConfig:

    def __init__(self, name="BF"):
        self.name = name
        self.exposure = None
        self.model = None

        if self.exposure is None:
            self.auto_exposure()

    def auto_exposure(self):
        self.exposure = 100

    def __repr__(self):
        return str(self.name)


class Microscope:
    def __init__(self):
        self.name = None
        self.mmc = get_mmc()
        self.cam = Camera(self.mmc)
        self.z = Focus(self.mmc)
        self.ch = Channel(self.mmc)

        self.stage = TwoD_XY_StagePositioner("", name="xy_stage")

    def snap(self, channel=None, exposure=None, num=1, delay=0):
        # run a blue sky count method with cameras
        # return uid

        if channel is not None:
            self.cam.set_channel(channel)

        if exposure is not None:
            self.cam.set_exposure(exposure)

        uid, = RE(count([self.cam, self.stage, self.z], num=num, delay=delay))
        return uid

    def count(self, channels, num, delay, *, md=None):
        chns = [ch.name for ch in channels]
        exps = [ch.exposure for ch in channels]
        yield from list_scan([self.cam, self.stage, self.z, self.ch, self.cam.exposure], self.ch, chns, self.cam.exposure, exps)

    def scan(self, channel=None, exposure=None, center=None, num=None):
        if channel is not None:
            self.cam.set_channel(channel)

        if exposure is not None:
            self.cam.set_exposure(exposure)

        if center is None:
            center = self.mmc.getXYPosition()

        x_center, y_center = center

        if num is None:
            num = 3

        full_range = num * axial_length()

        plan = spiral_square([self.cam, self.z], self.stage.x, self.stage.y, x_center=x_center, y_center=y_center,
                             x_range=full_range, y_range=full_range, x_num=num, y_num=num)

        uid, = RE(plan)

        return uid


if __name__ == "__main__":
    bf = ChannelConfig("BF")
    bf.exposure = 100
    bf.model = {"kind": "cyto",
                "diameter": 100}

    fitc = ChannelConfig("TRITC")
    fitc.exposure = 300
    fitc.model = {"kind": "nuclei",
                  "diameter": 50}

    m = Microscope()
    # channels
    # bluesky plans

    uid, = RE(m.count([fitc, bf], num=1, delay=None))
    imgs = images_from_uid(uid)
    napari.view_image(imgs)
