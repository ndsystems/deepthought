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

    def generate_positions(self, relative=True):
        positions = [[self.estimate_axial_length(), 0]] * 10 + [[0, self.estimate_axial_length()]] * 10
        positions = positions + [[-self.estimate_axial_length(), 0]] * 10 + [[0, -self.estimate_axial_length()]] * 10
        return positions

class Microscope(BaseMicroscope):
    def __init__(self):
        super().__init__()
        self.fg = FrameGroup()
        self.fv = FrameGroupVisualizer()
        self.fg.subscribe(self.fv)

    def snap(self, positions=None, channel=None, num=1):
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

    def scan(self, positions=None, channel=None, secondary_channel=None, num=100):
        detectors = [self.cam, self.stage,
                     self.z, self.ch, self.cam.exposure]
        
        if positions is None:
            positions = self.generate_positions()

        if channel is not None:
            print(f"moving to {channel}")
            yield from plan_stubs.mv(self.ch, channel.name)
            yield from plan_stubs.mv(self.cam.exposure, channel.exposure)

        def inner_loop():
            frame_positions = []
            yield from plan_stubs.open_run()

            for pos in positions:
                x = yield from plan_stubs.rd(self.stage.x)
                y = yield from plan_stubs.rd(self.stage.y)

                yield from plan_stubs.trigger_and_read(detectors)
                yield from plan_stubs.wait()

                img = yield from plan_stubs.rd(self.cam)
                frame_positions.append([x, y])
                frame = Frame(img, [x, y], channel.model, self.unit_physical_length())
                self.fg.add(frame)
                if frame.count > 20:
                    print(f"moving to {secondary_channel}")
                    yield from plan_stubs.mv(self.ch, secondary_channel.name)
                    yield from plan_stubs.mv(self.cam.exposure, secondary_channel.exposure)

                    yield from plan_stubs.trigger_and_read(detectors)
                    yield from plan_stubs.wait()

                    img = yield from plan_stubs.rd(self.cam)
                    frame.add_secondary(img)

                    print(f"moving to {channel}")
                    yield from plan_stubs.mv(self.ch, channel.name)
                    yield from plan_stubs.mv(self.cam.exposure, channel.exposure)
                
                self.fg.notify(frame)

                if self.fg.count >= num:
                    break

                yield from plan_stubs.mvr(self.stage.x, pos[0])
                yield from plan_stubs.mvr(self.stage.y, pos[1])
                
            yield from plan_stubs.close_run()

        yield from inner_loop()

class FrameGroupVisualizer:
    def __init__(self):
        self.fig, self.ax = plt.subplots(1, 3, figsize=(9, 3), dpi=120)
        self.ax[0].set_aspect('equal')
        self.ax[1].set_xlabel("Nuclear Size")
        self.ax[1].set_ylabel("Frequency")
        self.ax[0].set_xlabel("Stage X (um)")
        self.ax[0].set_ylabel("Stage Y (um)")
        self.ax[2].set_xlabel("DAPI mean")
        self.ax[2].set_ylabel("FITC mean")
        self.frame_n = 1
        self.object_count = 0
        self.nuclear_size = []
        plt.tight_layout()
        plt.show(block=False)

    def update(self, frame):
        object_coords = [ob.xy for ob in frame._objects]
        self.nuclear_size.extend([ob.area for ob in frame._objects])

        self.object_count += len(object_coords)
        coords_x = [_[0] for _ in object_coords]
        coords_y = [_[1] for _ in object_coords]
        
        intensity_primary = [ob.intensity_image.mean() for ob in frame._objects]
    
        intensity_secondary = [ob.intensity_image.mean() for ob in frame.secondary_objects]

        if self.frame_n == 1:
            self.ax[0].set_title(f"N = {self.object_count} from {self.frame_n} frames")
            self.ax[0].scatter(coords_x, coords_y,  s=7)
            self.ax[1].hist(self.nuclear_size)
            if len(intensity_secondary) >= 0:
                self.ax[2].scatter(intensity_primary, intensity_secondary,  s=7)

        else:
            self.ax[0].set_title(f"N = {self.object_count} from {self.frame_n} frames")
            self.ax[0].scatter(coords_x, coords_y,  s=7)
            self.ax[1].cla()
            self.ax[1].set_xlabel("Nuclear Size")
            self.ax[1].set_ylabel("Frequency")
            self.ax[1].hist(self.nuclear_size)
        
            if len(intensity_secondary) >= 0:
                self.ax[2].scatter(intensity_primary, intensity_secondary,  s=7)

        self.frame_n += 1
        self.fig.canvas.draw()


class FrameGroup:
    def __init__(self):
        self.frames = []
        self.count = 0
        self._subscribers = []

    def add(self, frame):
        self.frames.append(frame)
        _, objs = frame.seg()
        self.count += len(objs)

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
        self.secondary_image = None
        self._objects = []
        self.secondary_objects = []
        self.coords = coords
        self.pixel_size = pixel_size
        self.model = model
        
    def seg(self):
        self.label = segment(self.image, **self.model)
        self._objects = find_object_properties(self.label, self.image, self.coords, self.pixel_size)
        self.count = len(self._objects)
        return self.label, self._objects

    def add_secondary(self, image):
        self.secondary_image = image
        self.secondary_objects = find_object_properties(self.label, self.secondary_image, self.coords, self.pixel_size)

    def view(self):
        v = napari.view_image(self.image)
        v.view_image(self.secondary_image)
        v.add_labels(self.label)

def inspect_plan(plan):
    msgs = list(plan)
    for m in msgs:
        print(m)


if __name__ == "__main__":
    tritc = ChannelConfig("TRITC")
    tritc.exposure = 500
    tritc.model = {"kind": "nuclei",
                  "diameter": 100}

    dapi = ChannelConfig("DAPI")
    dapi.exposure = 30
    dapi.model = {"kind": "nuclei",
                  "diameter": 100}

    fitc = ChannelConfig("FITC")
    fitc.exposure = 300
    fitc.model = {"kind": "nuclei",
                  "diameter": 100}

    m = Microscope()
    m.mmc.setXYPosition(-32808.46, -1314.0)

    plan = m.scan(channel=dapi, secondary_channel=fitc, num=10000)
    uid, = RE(plan)


# pchk1 gh2ax, 10000 cells
# s phase and non s phase - live cell