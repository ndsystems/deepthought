from cycler import cycler
import numpy as np
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine, plans, plan_stubs, plan_patterns, utils
from bluesky import preprocessors as bpp
from devices import Camera, Focus, TwoD_XY_StagePositioner, get_mmc, Channel, AutoFocus
from compute import axial_length
from bluesky.callbacks.broker import post_run
from data import db
import napari


bec = BestEffortCallback()
bec.disable_plots()

RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)


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
        self.af = AutoFocus(self.mmc)

        self.stage = TwoD_XY_StagePositioner("", name="xy_stage")

    def estimate_axial_length(self):
        num_px = 2048
        mag = 60
        binning = 1
        det_px_size = 6.5  # um
        ax_len = axial_length(num_px, mag, binning, det_px_size)
        return ax_len

    def snap(self, channel=None, exposure=None, num=1, delay=0):
        # run a blue sky count method with cameras
        # return uid

        if channel is not None:
            self.cam.set_channel(channel)

        if exposure is not None:
            self.cam.set_exposure(exposure)

        uid, = RE(plans.count(
            [self.cam, self.stage, self.z], num=num, delay=delay))
        return uid

    def count(self, channels, num, delay, *, md=None):
        chns = [ch.name for ch in channels]
        exps = [ch.exposure for ch in channels]

        x_coords = []
        y_coords = []

        yield from plans.list_scan([self.cam, self.stage, self.z, self.ch, self.cam.exposure],
                                   self.stage.x, x_coords,
                                   self.stage.y, y_coords,
                                   self.ch, chns,
                                   self.cam.exposure, exps)

    def initial_scan(self, channel, center, num):
        detectors = [self.cam, self.stage, self.z, self.ch, self.cam.exposure]

        x_center, y_center = center

        full_range = num * self.estimate_axial_length()

        x_range = full_range
        y_range = full_range
        x_num = num
        y_num = num

        pattern_args = dict(x_motor=self.stage.x, y_motor=self.stage.y, x_center=x_center,
                            y_center=y_center, x_range=x_range, y_range=y_range,
                            x_num=x_num, y_num=y_num)
        # cycler for x,y
        cyc = plan_patterns.spiral_square_pattern(**pattern_args)

        def inner_initial_scan():
            yield from plans.scan_nd(detectors, cyc, per_step=self.per_nd_step)

        # set channel, and exposure time
        yield from plan_stubs.mv(self.ch, channel.name)
        yield from plan_stubs.mv(self.cam.exposure, channel.exposure)

        return (yield from inner_initial_scan())

    def per_nd_step(self, detectors, step, pos_cache):
        @bpp.reset_positions_decorator([self.z])
        @bpp.relative_set_decorator([self.z])
        def zscan():
            for z in np.linspace(-10, 10, 10):
                yield from plan_stubs.mv(self.z, z)
                yield from plan_stubs.trigger_and_read([self.z] + detectors)

        def move():
            yield from plan_stubs.checkpoint()
            grp = utils.short_uid('set')
            for motor, pos in step.items():
                if pos == pos_cache[motor]:
                    # This step does not move this motor.
                    continue
                yield from plan_stubs.abs_set(motor, pos, group=grp)
                pos_cache[motor] = pos
            yield from plan_stubs.wait(group=grp)

        yield from move()
        yield from zscan()


if __name__ == "__main__":
    bf = ChannelConfig("BF")
    bf.exposure = 100
    bf.model = {"kind": "cyto",
                "diameter": 100}

    tritc = ChannelConfig("TRITC")
    tritc.exposure = 350
    tritc.model = {"kind": "nuclei",
                   "diameter": 50}

    m = Microscope()

    # initial scan
    center = [-31706.9, -833.0]
    num = 2

    uid, = RE(m.initial_scan(tritc, center, num))
    # print(list(m.initial_scan(tritc, center, num)))

    imgs = images_from_uid(uid)
    napari.view_image(imgs)
