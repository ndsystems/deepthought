import numpy as np
from bluesky import plan_stubs, utils
from devices import Camera, Focus, Channel, AutoFocus, XYStage
import threading
from optimization import shannon_dct
from scanspec.specs import Line
from scanspec.regions import Circle
from frames import ObjectsAlbum, Frame, SingleLabelFrames
from ophyd import Signal

class Disk:
    def __init__(self):
        self.center = [0, 0]
        self.diameter = 13 * 1000  # mm - > um
        self.radius = self.diameter / 2

class BaseMicroscope:
    """Basic abstraction of a microscope.

    Microscope requires a MMCore control object, which is passed on to ophyd
    Device definitions, such as Camera, Focus, XYStage, etc. In this level of
    abstraction, the devices of the microscope are (largely) operatered within
    bluesky plans.

    autofocus adapted from 
    https://github.com/mdcurtis/micromanager-upstream/blob/master/scripts/AutoExpose.bsh
    """

    def __init__(self, mmc, name=None):
        self.mmc = mmc
        self.name = name
        self.cam = Camera(self.mmc)
        self.z = Focus(self.mmc)
        self.ch = Channel(self.mmc)
        self.af = AutoFocus(self.mmc)
        self.stage = XYStage(self.mmc)
        self.detectors = [self.stage,
                          self.z, self.ch, self.cam.exposure, self.cam]

    def pixel_size(self):
        # temporary work around
        # do not access mmc directly from Microscope. 
        # this has to be abstracted as an Objective ophyd device.
        obj_state = int(self.mmc.getProperty("Objective", "State"))
        if obj_state == 4:
            mag = 100
        elif obj_state == 3:
            mag = 60

        binning = int(self.mmc.getProperty("left_port", "Binning")[0])

        det_px_size = 6.5  # um for andor zyla
        pixel_size = (det_px_size /mag) * binning
    
        return pixel_size

    def estimate_axial_length(self):
        """estimate axial length of the detection field of view."""
        num_px = self.mmc.getImageWidth()
        ax_len = self.pixel_size() * num_px
        return ax_len

    def generate_grid(self, initial_x, initial_y, num, pos="middle"):
        """generate a grid around a point, with width proportional to
        axial length"""
        width = self.estimate_axial_length()/2

        if pos == "middle":
            start_x = initial_x - (width*num)
            stop_x = (width*(num+1)) + initial_x

            start_y = initial_y - (width*num)
            stop_y = (width*(num+1)) + initial_y

        if pos == "left":
            start_x = initial_x
            stop_x = (width*(num+1)) + start_x

            start_y = initial_y
            stop_y = (width*(num+1)) + start_y

        spec = Line("y", start_y, stop_y, num) * \
            ~Line("x", start_x, stop_x, num)
        
        disk = Disk()
        circle_spec = spec & Circle("x", "y", *disk.center, disk.radius)
        return circle_spec

    def auto_focus(self):
        initial_z = yield from plan_stubs.rd(self.z)

        pass

    def auto_exposure(self):
        """find the best exposure given current exposure"""
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
            yield from self.auto_exposure()

        next_exposure = aim * max_possible / max_value * exposure

        if next_exposure > max_exposure:
            return

        yield from plan_stubs.mv(self.cam.exposure, int(next_exposure))

        if (max_value/max_possible) > low_fraction:
            yield from self.auto_exposure()

    def snap_image_and_other_readings_too(self, channel=None):
        """trigger the camera and other devices associated with snapping
        an image"""
        try:
            if channel is not None:
                yield from self.set_channel(channel)
            yield from plan_stubs.trigger_and_read(self.detectors)
            yield from plan_stubs.wait()
        except utils.FailedStatus:
            print("RECOVERING FROM FAILURE")
            yield from plan_stubs.sleep(5)
            yield from self.snap_image_and_other_readings_too()

    def set_channel(self, channel):
        """set MMConfigGroup and camera exposure"""
        yield from plan_stubs.mv(self.ch, channel.name)

        if channel.exposure == "auto":
            yield from self.auto_exposure()
        else:
            yield from plan_stubs.mv(self.cam.exposure, channel.exposure)


class Microscope(BaseMicroscope):
    """A device to extract objects from images."""

    def __init__(self, mmc):
        super().__init__(mmc=mmc)
        self.album = ObjectsAlbum()

    def anisotropy_objects(self, channel):
        """experiment with anisotropy

        step 1 - image frames of interest
        step 2 - extract parallel and perpendicular fields
        step 3 - compute anisotropy
        step 4 - segment objects

        """

        yield from self.snap_image_and_other_readings_too(channel)

        img = yield from plan_stubs.rd(self.cam)
        x, y = yield from plan_stubs.rd(self.stage)
        frame = AnisotropyFrame(img, coords=[x, y])

        self.album.add_frame(frame)

    def snap_an(self, channels):
        yield from plan_stubs.open_run()
        for ch in channels:
            yield from self.anisotropy_objects(ch)
        yield from plan_stubs.close_run()

    def scan_an_t(self, channels, cycles=3, delta_t=3):
        for _ in range(cycles):
            yield from self.snap_an(channels)
            yield from plan_stubs.sleep(delta_t)

    def scan_an_xy(self, channels, grid=None):
        for point in grid.midpoints():
            coords = [float(point["x"]), float(point["y"])]
            yield from plan_stubs.mv(self.stage, coords)
            yield from self.snap_an(channels)

    def scan_an_xy_t(self, channels, num=2, cycles=1, delta_t=1):
        """Scan a grid over time and compute anisotropy image.
        """
        self.current_t = 0

        initial_coords = yield from plan_stubs.rd(self.stage)

        grid = self.generate_grid(*initial_coords, pos="left", num=num)

        def inner_loop():
            self.album.set_current_group(self.current_t)
            yield from self.scan_an_xy(channels, grid=grid)
            yield from plan_stubs.sleep(delta_t)
            self.current_t += 1

        # time recursion
        while True:
            if self.current_t >= cycles:
                yield from inner_loop()
                break

            else:
                yield from inner_loop()

    def cellular_objects(self, channels):
        s = Signal(name="label", value=0)
        uid = yield from plan_stubs.open_run()

        frame_collection = SingleLabelFrames(channels)

        for ch in channels:
            yield from self.snap_image_and_other_readings_too(ch)
            img = yield from plan_stubs.rd(self.cam)
            x, y = yield from plan_stubs.rd(self.stage)
            pixel_size = self.pixel_size()
            frame = Frame(img, coords=[x, y], channel=ch, pixel_size=pixel_size)
            frame_collection.add_frame(frame)

        objects = frame_collection.get_objects()
        label = frame_collection.primary_label
        yield from plan_stubs.mv(s, label)
        yield from plan_stubs.trigger_and_read([s], name="label")
        self.album.add_objects(uid, objects)
        yield from plan_stubs.close_run()

    def scan_xy(self, channels, grid=None, num=8, initial_coords=None):
        if initial_coords is None:
            initial_coords = yield from plan_stubs.rd(self.stage)

        if grid is None:
            grid = self.generate_grid(*initial_coords, pos="left", num=num)

        for point in grid.midpoints():
            coords = [float(point["x"]), float(point["y"])]
            yield from plan_stubs.mv(self.stage, coords)
            yield from self.cellular_objects(channels)
        
def inspect_plan(plan):
    msgs = list(plan)
    for m in msgs:
        print(m)
