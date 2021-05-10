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
from databroker import Broker
from configs import store_disk
from devices import Camera, Focus, TwoD_XY_StagePositioner, get_mmc

# other devices have to be added.
# to figure out where


bec = BestEffortCallback()
bec.disable_plots()

db = Broker.named("temp")


RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)

if store_disk:
    from bluesky.callbacks.broker import LiveTiffExporter

    template = "output_dir/{start[scan_id]}/{event[seq_num]}.tiff"
    live = LiveTiffExporter("camera",
                            template=template,
                            db=db,
                            overwrite=True)
    RE.subscribe(live)


class Microscope:
    def __init__(self):
        self.name = None
        self.mmc = get_mmc()
        self._cam = [Camera(self.mmc)]
        self.z = Focus(self.mmc)
        self.stage = TwoD_XY_StagePositioner("", name="xy_stage")

    def snap(self, num=1, delay=0):
        # run a blue sky count method with cameras
        # return uid
        uid, = RE(count(self._cam, num=num, delay=delay))

        # https://nsls-ii.github.io/databroker/generated/databroker.Header.table.html#databroker.Header.table
        header = db[uid]

        img = np.stack(header.table()["camera"].array)

        return img

    def scan(self, center=None, range=None, num=None):
        if center is None:
            center = self.mmc.getXYPosition()
            x_center, y_center = center

        plan = spiral_square(self._cam, self.stage.x, self.stage.y, x_center=x_center, y_center=y_center,
                             x_range=1000, y_range=1000, x_num=5, y_num=5)

        uid, = RE(plan)
        header = db[uid]
        img = np.stack(header.table()["camera"].array)
        return img
