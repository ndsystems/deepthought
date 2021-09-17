import logging
logging.getLogger("imported_module").setLevel(logging.WARNING)

from cycler import cycler
import numpy as np
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine, plans, plan_stubs, plan_patterns, utils
from bluesky import preprocessors as bpp
from devices import Camera, Focus, TwoD_XY_StagePositioner, get_mmc, Channel, AutoFocus, SoftMMCPositioner
from compute import axial_length
from bluesky.callbacks.broker import post_run, BrokerCallbackBase
from data import db
import napari
from detection import segment, find_object_properties
import matplotlib.pyplot as plt
import threading

bec = BestEffortCallback()
bec.disable_plots()

RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)


def images_from_uid(uid):
    header = db[uid]
    imgs = np.stack(header.table()["image"].to_numpy())
    return imgs


class Disk:
    def __init__(self, center, num):
        self.center = center
        self.diameter = 13 * 1000  # mm - > um

        # parameter for num of axial widths
        self.num = num


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

class BaseMicroscope:
    def __init__(self):
        self.name = None
        self.mmc = get_mmc()
        self.cam = Camera(self.mmc)
        self.z = Focus(self.mmc)
        self.ch = Channel(self.mmc)
        self.af = AutoFocus(self.mmc)
        self.stage = TwoD_XY_StagePositioner("", name="xy_stage")
    
    def unit_physical_length(self):
        num_px = 2048
        mag = 60
        binning = 1
        det_px_size = 6.5  # um
        unit_pixel_in_micron = (det_px_size / mag) * binning

        return unit_pixel_in_micron

    def estimate_axial_length(self):
        num_px = 2048
        mag = 60
        binning = 1
        det_px_size = 6.5  # um
        ax_len = axial_length(num_px, mag, binning, det_px_size)
        return ax_len

class Microscope(BaseMicroscope):
    def __init__(self):
        super().__init__()
        self.fg = FrameGroup()
        self.fv = FrameGroupVisualizer()
        self.fg.subscribe(self.fv)

    def snap(self, positions=None, channel=None, num=10):
        detectors = [self.cam, self.stage,
                     self.z, self.ch, self.cam.exposure]

        if channel is not None:
            print(f"moving to {channel}")
            yield from plan_stubs.mv(self.ch, channel.name)
            yield from plan_stubs.mv(self.cam.exposure, channel.exposure)

        def inner_loop():
            yield from plan_stubs.open_run()
            for _ in range(num):
                yield from plan_stubs.trigger_and_read(detectors)
                yield from plan_stubs.wait()

                img = yield from plan_stubs.rd(self.cam)
                x = yield from plan_stubs.rd(self.stage.x)
                y = yield from plan_stubs.rd(self.stage.y)
                self.fg.add(Frame(img, [x, y], channel.model, self.unit_physical_length()))

                yield from plan_stubs.mvr(self.stage.x, -self.estimate_axial_length())
            yield from plan_stubs.close_run()

        yield from inner_loop()

class FrameGroupVisualizer:
    def __init__(self):
        self.fig, self.ax = plt.subplots(dpi=120)
        self.ax.set_aspect('equal')
        self.frame_n = 1
        self.object_count = 0
        plt.show(block=False)

    def update(self, frame):
        object_coords = [ob.xy for ob in frame._objects]
        self.object_count += len(object_coords)
        coords_x = [_[0] for _ in object_coords]
        coords_y = [_[1] for _ in object_coords]
        print(f"N ==== {self.frame_n}")

        if self.frame_n == 1:
            self.ax.scatter(coords_x, coords_y, label=frame.coords, s=7)
            self.frame_n += 1
        else:
            self.ax.set_title(f"N = {self.object_count} from {self.frame_n} frames")
            self.ax.scatter(coords_x, coords_y, label=frame.coords, s=7)
            self.frame_n += 1

        self.fig.canvas.draw()
        plt.legend()
            

class FrameGroup:
    def __init__(self):
        self.frames = []
        self._subscribers = []

    def add(self, frame):
        def wait():
            self.frames.append(frame)
            img = frame.seg()
            self.notify(frame)
        threading.Thread(target=wait).start()

    def subscribe(self, subscriber):
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)

    def notify(self, frame):
        for subscriber in self._subscribers:
            threading.Thread(target=subscriber.update, args=(frame,)).start()

    def __getitem__(self, item):
        return self.frames[item]

class Frame:
    def __init__(self, image, coords, model, pixel_size):
        self.image = image
        self.coords = coords
        self.model = model
        self.pixel_size = pixel_size

    def seg(self):
        self.label = segment(self.image, **self.model)
        self._objects = find_object_properties(self.label, self.image, self.coords, self.pixel_size)
        return self.label

    def view(self):
        v = napari.view_image(self.image)
        v.add_labels(self.label)

    def hist(self):
        means = [_.intensity_image.mean() for _ in self._objects]
        plt.hist(means)
        plt.show()

def inspect_plan(plan):
    msgs = list(plan)
    for m in msgs:
        print(m)


if __name__ == "__main__":
    dapi = ChannelConfig("DAPI")
    dapi.exposure = 50
    dapi.model = {"kind": "nuclei",
                  "diameter": 100}

    m = Microscope()

    plan = m.snap(channel=dapi)
    uid, = RE(plan)
