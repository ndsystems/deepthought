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
            self.exposure = "auto"

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

    def auto_focus(self):
        pass

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

    

def inspect_plan(plan):
    msgs = list(plan)
    for m in msgs:
        print(m)


