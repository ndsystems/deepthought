"""
To do:

1. configure number of cameras and camera parameters easily from user code.
2. xy, z into a position object.
    Stage.x

"""
import numpy as np
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.plans import count, scan, spiral_square
from configs import store_disk
from devices import Camera, Focus, TwoD_XY_StagePositioner, get_mmc
from compute import axial_length
from bluesky.callbacks.broker import post_run
from data import db
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


class Microscope:
    def __init__(self):
        self.name = None
        self.mmc = get_mmc()
        self._cam = Camera(self.mmc)
        self.z = Focus(self.mmc)
        self.stage = TwoD_XY_StagePositioner("", name="xy_stage")

    def snap(self, channel=None, exposure=None):
        # run a blue sky count method with cameras
        # return uid

        if channel is not None:
            self._cam.set_channel(channel)

        if exposure is not None:
            self._cam.set_exposure(exposure)

        uid, = RE(count([self._cam, self.stage, self.z]))
        return uid

    def scan(self, channel=None, exposure=None, center=None, num=None):
        if channel is not None:
            self._cam.set_channel(channel)

        if exposure is not None:
            self._cam.set_exposure(exposure)

        if center is None:
            center = self.mmc.getXYPosition()

        x_center, y_center = center

        if num is None:
            num = 3

        full_range = num * axial_length()

        plan = spiral_square([self._cam, self.z], self.stage.x, self.stage.y, x_center=x_center, y_center=y_center,
                             x_range=full_range, y_range=full_range, x_num=num, y_num=num)

        uid, = RE(plan)

        return uid
