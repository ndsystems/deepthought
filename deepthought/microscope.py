from cycler import cycler
import numpy as np
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine, plans, plan_stubs, plan_patterns, utils
from bluesky import preprocessors as bpp
from devices import Camera, Focus, Channel, AutoFocus, XYStage
from compute import axial_length
from bluesky.callbacks.broker import BrokerCallbackBase
from data import db
import napari
import matplotlib.pyplot as plt
import threading
from optimization import shannon_dct
from scanspec.specs import Line
import pickle

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
    def __init__(self, name=None, mmc=None):
        self.name = name
        self.mmc = mmc
        self.cam = Camera(self.mmc)
        self.z = Focus(self.mmc)
        self.ch = Channel(self.mmc)
        self.af = AutoFocus(self.mmc)
        self.stage = XYStage(self.mmc)
    
    def estimate_axial_length(self):
        num_px = self.mmc.getImageWidth()
        
        obj_state = int(self.mmc.getProperty( "Objective", "State"))
        if obj_state == 4:
            mag = 100
        elif obj_state == 3:
            mag = 60
        binning = int(self.mmc.getProperty("left_port", "Binning")[0])

        det_px_size = 6.5  # um for andor zyla
        ax_len = axial_length(num_px, mag, binning, det_px_size)

        return ax_len


    def generate_grid(self, initial_x, initial_y, num):
        width = self.estimate_axial_length()/2
        
        start_x = initial_x - (width*num) 
        stop_x = (width*(num+1)) + initial_x
        
        start_y = initial_y - (width*num)
        stop_y = (width*(num+1)) + initial_y

        spec = Line("y", start_y, stop_y, num) * Line("x", start_x, stop_x, num)
        return spec

class Microscope(BaseMicroscope):
    def __init__(self, mmc):
        super().__init__(mmc=mmc)
        self.detectors = [self.stage,
                     self.z, self.ch, self.cam.exposure, self.cam]

    def auto_exposure(self):
        # adapted from 
        # https://github.com/mdcurtis/micromanager-upstream/blob/master/scripts/AutoExpose.bsh

        max_possible = 4095
        max_exposure = 5000
        saturated = 0.95
        too_bright = 5
        aim = 0.5
        low_fraction = 0.5

        # snap image
        yield from self.snap_image_and_other_readings_too()
        img = yield from plan_stubs.rd(self.cam)
        exposure = yield from plan_stubs.rd(self.cam.exposure)
        
        max_value = img.max()
        
        if max_value > (max_possible * saturated):
            next_exposure = (1/too_bright) * exposure
            print(f"too bright! next_exposure: {next_exposure}")
            yield from plan_stubs.mv(self.cam.exposure, next_exposure)
            yield from auto_exposure()
        
        next_exposure = aim * max_possible / max_value * exposure
        
        if next_exposure > max_exposure:
            return
        
        yield from plan_stubs.mv(self.cam.exposure, int(next_exposure))
        
        if (max_value/max_possible) > low_fraction:
            yield from auto_exposure()
        
    def snap_image_and_other_readings_too(self):
        try:
            yield from plan_stubs.trigger_and_read(self.detectors)
            yield from plan_stubs.wait()
        except utils.FailedStatus:
            print("RECOVERING FROM FAILURE")
            yield from plan.plan_stubs.sleep(5)
            yield from self.snap_image_and_other_readings_too()

    def set_channel(self, channel):
        yield from plan_stubs.mv(self.ch, channel.name)
        if channel.exposure == "auto":
            yield from self.auto_exposure()
        else:
            yield from plan_stubs.mv(self.cam.exposure, channel.exposure)


    def scan_grid(self, channels, per_step_xy=None):
        # create a grid
        initial_x, initial_y = yield from plan_stubs.rd(self.stage)
        grid = self.generate_grid(initial_x=initial_x, initial_y=initial_y, num=2)

        def inner_loop():
            # iterate thru the scanspec object for grid
            for point in grid.midpoints():
                # scanspec to device definition adapter
                coords = [float(point["x"]), float(point["y"])]
                yield from plan_stubs.mv(self.stage, coords)
                for channel in channels:
                    yield from self.set_channel(channel)
                    yield from self.snap_image_and_other_readings_too()
                    img = yield from plan_stubs.rd(self.cam)
                    x, y = yield from plan_stubs.rd(self.stage)
                    if per_step_xy is not None:
                        try:
                            per_step_xy(img)
                        except:
                            print('error running func on image')
                            pass

        yield from plan_stubs.open_run()
        yield from inner_loop()
        yield from plan_stubs.close_run()

    

class FrameGroupVisualizer:
    def __init__(self):
        self.fig, self.ax = plt.subplots(1, 3, figsize=(9, 3), dpi=120)
        self.ax[0].set_aspect('equal')
        self.ax[1].set_xlabel("Nuclear Size")
        self.ax[1].set_ylabel("Frequency")
        self.ax[0].set_xlabel("Stage X (um)")
        self.ax[0].set_ylabel("Stage Y (um)")
        self.frame_n = 1
        self.object_count = 0
        self.nuclear_size = []
        plt.tight_layout()
        plt.show(block=False)

    def update_map(self, frame):
        object_coords = [ob.xy for ob in frame._objects]
        self.object_count += len(object_coords)
        coords_x = [_[0] for _ in object_coords]
        coords_y = [_[1] for _ in object_coords]

        self.ax[0].set_title(f"N = {self.object_count} from {self.frame_n} frames")
        self.ax[0].scatter(coords_x, coords_y,  s=7)

    def update_nuclear_size(self, frame):
        self.nuclear_size.extend([ob.area for ob in frame._objects])
        self.ax[1].hist(self.nuclear_size)
        self.ax[1].cla()
        self.ax[1].set_xlabel("Nuclear Size")
        self.ax[1].set_ylabel("Frequency")
        self.ax[1].hist(self.nuclear_size)

    def update_intensities(self, frame):
        if len(frame.secondary_images) > 1:
            self.ax[2].set_xlabel(f"{frame.secondary_images[0].channel} mean")
            self.ax[2].set_ylabel(f"{frame.secondary_images[1].channel} mean")
            intensity_secondary = [ob.intensity_image.mean() for ob in frame.secondary_images[0]._objects]
            intensity_secondary_2 = [ob.intensity_image.mean() for ob in frame.secondary_images[1]._objects]
            self.ax[2].scatter(intensity_secondary, intensity_secondary_2,  s=7)
    
    def update(self, frame):
        self.update_map(frame)
        self.update_nuclear_size(frame)
        self.update_intensities(frame)
        self.frame_n += 1
        self.fig.canvas.draw()

def detect_from_frame(frame):
    image = frame.image
    model = frame.channel.model
    label = segment(image, **model)
    return self.label

class Coords:
    def __init__(self, xy):
        self.xy = xy

   
class FrameGroupProcessor:
    def __init__(self):
        pass

    def update(self, frame):
        self.segment(frame)

    def segment(self, frame):
        img = frame.image
        model = frame.channel.model
        frame.label = segment(img, **model)

    def anisotropy(self, frame):
        ...

class TimeGroup:
    def __init__(self):
        self.timesteps = []
    
    def add(self, group):
        self.timesteps.append(group)
        
    def __getitem__(self, item):
        return self.timesteps[item]

    def __len__(self):
        return len(self.timesteps)

class FrameGroup:
    def __init__(self):
        self.frames = []
        self._subscribers = []
    
    def add(self, frame):
        self.frames.append(frame)
        self.notify()
    
    def __getitem__(self, item):
        return self.frames[item]

    def subscribe(self, processor):
        if processor not in self._subscribers:
            self._subscribers.append(processor)

    def notify(self):
        for _ in self._subscribers:
            _.update(self.frames[-1])

    def dump(self, t):
        with open(f'filename_{t}.pickle', 'wb') as handle:
            pickle.dump(self, handle)


class Frame:
    def __init__(self, channel, image, coords):
        self.channel = channel
        self.image = image
        self.coords = coords

def inspect_plan(plan):
    msgs = list(plan)
    for m in msgs:
        print(m)


class Experiments:
    # pcna time series for 24h - 100+ cells
    # pcna time series with NCS low dose (0.1ug/ml)
    #   * 6h

    # h2b- control cells - 2h /every 5minutes
    #   * 1ug/ml NCS
    #   * anisotropy imaging


    # cumulitivate histogram of intensity vs frequency
    ...