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
        num_px = 512
        mag = 60
        binning = 4
        det_px_size = 6.5  # um
        ax_len = axial_length(num_px, mag, binning, det_px_size)
        return ax_len

    def create_circle_square(self, center, num):
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

        return cyc

    def initial_scan(self, channels, center, num, focus=None, repeat_times=1, delay=0):
        if focus is not None:
            yield from plan_stubs.mv(self.af, False)
            yield from plan_stubs.mv(self.z, focus)
            yield from plan_stubs.mv(self.af, True)
            yield from plan_stubs.wait()

        detectors = [self.cam, self.stage,
                     self.z, self.ch, self.cam.exposure]

        cyc = self.create_circle_square(center, num)

        def inner_initial_scan():
            for _ in np.arange(repeat_times):
                yield from plans.scan_nd(detectors, cyc, per_step=self.per_nd_step)
                yield from plan_stubs.sleep(delay)

        # # set channel, and exposure time
        # yield from plan_stubs.mv(self.ch, channel.name)
        # yield from plan_stubs.mv(self.cam.exposure, channel.exposure)

        return (yield from inner_initial_scan())

    def per_nd_step_ch(self, detectors, step, pos_cache):
        def move():
            yield from plan_stubs.checkpoint()
            grp = utils.short_uid('set')
            for motor, pos in step.items():
                if pos == pos_cache[motor]:
                    # This step does not move this motor.
                    continue

                yield from plan_stubs.mv(motor, pos, group=grp)
                pos_cache[motor] = pos
            yield from plan_stubs.wait(group=grp)

        def per_channel():
            for channel in self.channels:
                yield from plan_stubs.checkpoint()
                yield from plan_stubs.mv(self.ch, channel.name)
                yield from plan_stubs.mv(self.cam.exposure, channel.exposure)

                yield from plan_stubs.trigger_and_read(detectors)

        yield from move()
        yield from per_channel()

    def ddc(self, channels, shape):
        detectors = [self.cam, self.stage,
                     self.z, self.ch, self.cam.exposure]

        self.channels = channels

        cyc = self.create_circle_square(shape.center, shape.num)

        def inner_initial_scan():
            yield from plans.scan_nd(detectors, cyc, per_step=self.per_nd_step_ch)

        return (yield from inner_initial_scan())

    def zscan(self, detectors, focus, microns, num_slices):
        z_list_abs = np.linspace(-microns, microns, num_slices) + focus

        # to prevent race
        yield from plan_stubs.sleep(1)

        for z_value in z_list_abs:
            yield from plan_stubs.mv(self.z, z_value)
            yield from plan_stubs.trigger_and_read(detectors)

    def per_nd_step(self, detectors, step, pos_cache):
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
        # move xy
        yield from move()

        # read the focus for the current xy
        focus_xy = yield from plan_stubs.rd(self.z)
        print(f"focus is {focus_xy}")
        # take a z scan
        try:
            yield from self.zdc_enabled_zscan(detectors, focus=focus_xy)
        except KeyboardInterrupt:
            yield from plan_stubs.mv(self.af, False)
            yield from plan_stubs.abs_set(self.z, focus_xy)
            yield from plan_stubs.mv(self.af, True)

    def zdc_enabled_zscan(self, detectors, focus):
        # assumption is, when AF is on, the z-value has
        # the right focus, despite the moving XY.
        # The Z-drift compensator has motor control, which
        # maintains focus on a continuous basis.

        # turn the AF off, so we have Z motor control
        yield from plan_stubs.mv(self.af, False)

        # take a relative Z-scan
        yield from self.zscan(detectors, focus, 8, 8)

        # restore motor position to original focus
        yield from plan_stubs.mv(self.z, focus)

        # turn on AF, Z motor control lost.
        yield from plan_stubs.mv(self.af, True)
        yield from plan_stubs.wait()

    def test(self, position=None, channel=None):
        detectors = [self.cam, self.stage,
                     self.z, self.ch, self.cam.exposure]

        if position is not None:
            print(f"moving to {position}")
            yield from plan_stubs.mv(self.stage, position)

        if channel is not None:
            print(f"moving to {channel}")
            yield from plan_stubs.mv(self.ch, channel.name)
            yield from plan_stubs.mv(self.cam.exposure, channel.exposure)

        def inner_loop():
            yield from plan_stubs.open_run()
            for _ in range(1000):
                yield from plan_stubs.trigger_and_read(detectors)
                yield from plan_stubs.sleep(1)
            yield from plan_stubs.close_run()

        yield from inner_loop()

    def focus(self, position=None, channel=None):
        if position is not None:
            print(f"moving to {position}")
            yield from plan_stubs.mv(self.stage, position)

        if channel is not None:
            print(f"moving to {channel}")
            yield from plan_stubs.mv(self.ch, channel.name)
            yield from plan_stubs.mv(self.cam.exposure, channel.exposure)

        detectors = [self.cam, self.stage,
                     self.z, self.ch, self.cam.exposure]

        def inner_loop():
            yield from plan_stubs.open_run()

            for _ in np.arange(2200, 2400, 100):
                yield from plan_stubs.mv(self.z, _)
                yield from plan_stubs.trigger_and_read(detectors)
                yield from plan_stubs.sleep(1)
            yield from plan_stubs.close_run()

        yield from inner_loop()


def inspect_plan(plan):
    msgs = list(plan)
    for m in msgs:
        print(m)


def view_uid(uid, shape=None):
    imgs = images_from_uid(uid)
    if shape is not None:
        imgs = imgs.reshape(shape)
    viewer = napari.view_image(imgs)
    napari.run()


class LiveImage(BrokerCallbackBase):
    """
    Stream 2D images in a cross-section viewer.

    Parameters
    ----------
    field : string
        name of data field in an Event
    fs: Registry instance
        The Registry instance to pull the data from
    cmap : str,  colormap, or None
        color map to use.  Defaults to gray
    norm : Normalize or None
       Normalization function to use
    limit_func : callable, optional
        function that takes in the image and returns clim values
    auto_redraw : bool, optional
    interpolation : str, optional
        Interpolation method to use. List of valid options can be found in
        CrossSection2DView.interpolation
    """

    def __init__(self, field="image", *, db=None, cmap=None, norm=None,
                 limit_func=None, auto_redraw=True, interpolation=None,
                 window_title=None):
        super().__init__((field,), db=db)
        self.field = field

    def event(self, doc):
        super().event(doc)
        data = doc['data'][self.field]
        self.update(data)

    def update(self, data):
        v = napari.view_image(data)
        napari.run(force=True, max_loop_level=2)


if __name__ == "__main__":
    bf = ChannelConfig("BF")
    bf.exposure = 200
    bf.model = {"kind": "cyto",
                "diameter": 10}

    fitc = ChannelConfig("FITC")
    fitc.exposure = 500
    fitc.model = {"kind": "nuclei",
                  "diameter": 50}

    dapi = ChannelConfig("DAPI")
    dapi.exposure = 50
    dapi.model = {"kind": "nuclei",
                  "diameter": 50}

    cy5 = ChannelConfig("Cy5")
    cy5.exposure = 500
    cy5.model = {"kind": "nuclei",
                 "diameter": 50}

    m = Microscope()

    # initial scan
    center = [-31928.780, -611.140]
    num = 10

    shape = Disk(center, num)
    channels = [dapi, bf]

    plan = m.ddc(channels, shape)
    uid, = RE(plan)
    # inspect_plan(plan)
    view_uid(uid,)
