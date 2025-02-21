import numpy as np
from typing import Optional, List, Tuple, Dict, Generator
from dataclasses import dataclass
from bluesky import plan_stubs, utils
from devices import Camera, Focus, Channel, AutoFocus, XYStage
import threading
from optimization import shannon_dct
from scanspec.specs import Line
from scanspec.regions import Circle
from frames import (
    ObjectsAlbum, 
    Frame, 
    SingleLabelFrames, 
    FrameMetadata,
    DetectedObject
)
from ophyd import Signal

@dataclass
class MicroscopeConfig:
    """Configuration parameters for microscope hardware."""
    detector_pixel_size: float = 6.5  # um for Andor Zyla
    max_exposure: float = 5000  # ms
    max_pixel_value: int = 4095
    exposure_target: float = 0.5
    saturation_threshold: float = 0.95

class MicroscopeHardware:
    """Handles all direct hardware interactions through MMCore."""
    
    def __init__(self, mmc):
        self._mmc = mmc
        self._initialize_devices()
        self.config = MicroscopeConfig()

    def _initialize_devices(self):
        """Initialize all microscope devices."""
        self.cam = Camera(self._mmc)
        self.z = Focus(self._mmc)
        self.ch = Channel(self._mmc)
        self.af = AutoFocus(self._mmc)
        self.stage = XYStage(self._mmc)
        self.detectors = [self.stage, self.z, self.ch, self.cam.exposure, self.cam]

    def get_pixel_size(self) -> float:
        """Calculate pixel size based on objective and binning."""
        obj_state = int(self._mmc.getProperty("Objective", "State"))
        magnification = 100 if obj_state == 4 else 60
        binning = int(self._mmc.getProperty("left_port", "Binning")[0])
        return (self.config.detector_pixel_size / magnification) * binning

    def estimate_axial_length(self):
        """estimate axial length of the detection field of view."""
        num_px = self._mmc.getImageWidth()
        ax_len = self.get_pixel_size() * num_px
        return ax_len

    def generate_grid(self, initial_x, initial_y, num, pos="middle"):
        """generate a grid around a point, with width proportional to
        axial length"""
        width = self.estimate_axial_length() / 2

        if pos == "middle":
            start_x = initial_x - (width * num)
            stop_x = (width * (num + 1)) + initial_x

            start_y = initial_y - (width * num)
            stop_y = (width * (num + 1)) + initial_y

        if pos == "left":
            start_x = initial_x
            stop_x = (width * (num + 1)) + start_x

            start_y = initial_y
            stop_y = (width * (num + 1)) + start_y

        spec = Line("y", start_y, stop_y, num) * ~Line("x", start_x, stop_x, num)

        disk = Disk()
        circle_spec = spec & Circle("x", "y", *disk.center, disk.radius)
        return circle_spec

    def auto_focus(self):
        initial_z = yield from plan_stubs.rd(self.z)

        pass

    async def auto_exposure(self):
        """Optimize exposure time based on image intensity."""
        while True:
            yield from self.snap_image_and_other_readings_too()
            img = yield from plan_stubs.rd(self.cam)
            exposure = yield from plan_stubs.rd(self.cam.exposure)
            
            max_value = img.max()
            if max_value > (self.config.max_pixel_value * self.config.saturation_threshold):
                next_exposure = exposure / 5
            else:
                next_exposure = (self.config.exposure_target * 
                               self.config.max_pixel_value / max_value * exposure)
                
            if next_exposure > self.config.max_exposure:
                return
                
            yield from plan_stubs.mv(self.cam.exposure, int(next_exposure))
            
            if (max_value / self.config.max_pixel_value) <= 0.5:
                break

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

    async def acquire_frame(self, coords: Tuple[float, float], channel: str) -> Frame:
        """Acquire a single frame with proper metadata."""
        image = yield from self.snap_image_and_other_readings_too()
        
        # Create frame with proper metadata
        frame = Frame(
            image=image,
            coords=coords,
            channel=channel,
            pixel_size=self.get_pixel_size()
        )
        return frame

class Disk:
    def __init__(self):
        self.center = [0, 0]
        self.diameter = 13 * 1000  # mm - > um
        self.radius = self.diameter / 2

class ExperimentController:
    """Manages experimental workflows and scanning patterns."""
    
    def __init__(self, hardware: MicroscopeHardware):
        self.hw = hardware
        self.album = ObjectsAlbum()
        self._current_frames: Dict[str, SingleLabelFrames] = {}

    def anisotropy_objects(self, channel):
        """experiment with anisotropy

        step 1 - image frames of interest
        step 2 - extract parallel and perpendicular fields
        step 3 - compute anisotropy
        step 4 - segment objects

        """

        yield from self.hw.snap_image_and_other_readings_too(channel)

        img = yield from plan_stubs.rd(self.hw.cam)
        x, y = yield from plan_stubs.rd(self.hw.stage)
        frame = AnisotropyFrame(img, coords=[x, y])

        self.album.add_frame(frame)

    async def snap_an(self, channels):
        yield from plan_stubs.open_run()
        for ch in channels:
            yield from self.anisotropy_objects(ch)
        yield from plan_stubs.close_run()

    async def scan_an_t(self, channels, cycles=3, delta_t=3):
        for _ in range(cycles):
            yield from await self.snap_an(channels)
            yield from plan_stubs.sleep(delta_t)

    async def scan_an_xy(self, channels, grid=None):
        for point in grid.midpoints():
            coords = [float(point["x"]), float(point["y"])]
            yield from plan_stubs.mv(self.hw.stage, coords)
            yield from await self.snap_an(channels)

    async def scan_an_xy_t(self, channels, num=2, cycles=1, delta_t=1):
        """Scan a grid over time and compute anisotropy image."""
        self.current_t = 0

        initial_coords = yield from plan_stubs.rd(self.hw.stage)

        grid = self.hw.generate_grid(*initial_coords, pos="left", num=num)

        async def inner_loop():
            self.album.set_current_group(self.current_t)
            yield from await self.scan_an_xy(channels, grid=grid)
            yield from plan_stubs.sleep(delta_t)
            self.current_t += 1

        # time recursion
        while True:
            if self.current_t >= cycles:
                yield from await inner_loop()
                break

            else:
                yield from await inner_loop()

    async def cellular_objects(self, channels):
        s = Signal(name="label", value=0)
        uid = yield from plan_stubs.open_run()

        frame_collection = SingleLabelFrames()

        for ch in channels:
            yield from self.hw.snap_image_and_other_readings_too(ch)
            img = yield from plan_stubs.rd(self.hw.cam)
            x, y = yield from plan_stubs.rd(self.hw.stage)
            pixel_size = self.hw.get_pixel_size()
            frame = Frame(img, coords=[x, y], channel=ch, pixel_size=pixel_size)
            frame_collection.add_frame(frame)

        detected_objects = frame_collection.get_objects()
        self.album.add_object_collection(uid, detected_objects)

        label = frame_collection.primary_label
        yield from plan_stubs.mv(s, label)
        yield from plan_stubs.trigger_and_read([s], name="label")

        yield from plan_stubs.close_run()

    async def scan_xy(self, 
                     channels: List[str], 
                     grid: Optional[Tuple[int, int]] = None, 
                     num: int = 8, 
                     initial_coords: Optional[Tuple[float, float]] = None):
        """Perform XY scanning with improved error handling."""
        try:
            current_pos = initial_coords or (0.0, 0.0)
            
            # Generate scanning positions
            positions = self._generate_scan_positions(grid, num, current_pos)
            
            for pos in positions:
                # Move to position
                yield from plan_stubs.mv(self.hw.stage, *pos)
                
                # Acquire and process frames
                collection_id = await self.acquire_multichannel(pos, channels)
                
                # Optional: wait for stage settling
                yield from plan_stubs.sleep(0.1)
                
        except Exception as e:
            # Add proper logging here
            raise MicroscopeError(f"Scan failed: {str(e)}")

    def _generate_scan_positions(self, 
                               grid: Optional[Tuple[int, int]], 
                               num: int, 
                               start_pos: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate scanning positions based on parameters."""
        # Implementation of scanning pattern generation
        # ... existing code ...
        pass

    async def acquire_multichannel(self, coords: Tuple[float, float], channels: List[str]) -> str:
        """Acquire frames for multiple channels at current position."""
        collection_id = f"pos_{coords[0]}_{coords[1]}"
        frame_collection = SingleLabelFrames()
        
        for channel in channels:
            frame = await self.hw.acquire_frame(coords, channel)
            frame_collection.add_frame(frame)
            
        # Process the collection and add to album
        objects = frame_collection.get_objects()
        self.album.add_collection(collection_id, objects)
        
        # Cleanup frames after processing
        for frame in frame_collection.frames:
            frame.clean_up()
            
        return collection_id

    def get_detected_objects(self) -> List[DetectedObject]:
        """Get all detected objects from the album."""
        return self.album.detected_objects

class Plans:
    """Collection of experimental plans that can be executed by the RunEngine."""
    
    @staticmethod
    def grid_scan(
        microscope: 'Microscope',
        channels: List[str],
        grid: Optional[Tuple[int, int]] = None,
        num: int = 8,
        initial_coords: Optional[Tuple[float, float]] = None,
        settle_time: float = 0.1
    ) -> Generator:
        """
        Plan for performing a grid scan.
        
        Parameters
        ----------
        microscope : Microscope
            The microscope instance to use for scanning
        channels : List[str]
            List of channel names to acquire
        grid : Tuple[int, int], optional
            Grid dimensions (rows, cols)
        num : int
            Number of positions to scan if grid not specified
        initial_coords : Tuple[float, float], optional
            Starting coordinates for the scan
        settle_time : float
            Time to wait for stage settling between positions
            
        Yields
        ------
        Generator
            Bluesky plan messages
        """
        try:
            current_pos = initial_coords or (0.0, 0.0)
            positions = microscope._generate_scan_positions(grid, num, current_pos)
            
            yield from plan_stubs.open_run()
            
            for pos in positions:
                # Move to position
                yield from plan_stubs.mv(microscope.hardware.stage, *pos)
                
                # Acquire frames for each channel
                for channel in channels:
                    yield from microscope.hardware.snap_image_and_other_readings_too(channel)
                
                # Wait for settling
                if settle_time > 0:
                    yield from plan_stubs.sleep(settle_time)
            
            yield from plan_stubs.close_run()
            
        except Exception as e:
            raise MicroscopeError(f"Grid scan failed: {str(e)}")
    
    @staticmethod
    def auto_focus(microscope: 'Microscope') -> Generator:
        """
        Plan for auto-focusing the microscope.
        
        Parameters
        ----------
        microscope : Microscope
            The microscope instance to focus
            
        Yields
        ------
        Generator
            Bluesky plan messages
        """
        yield from microscope.hardware.auto_focus()
    
    @staticmethod
    def auto_exposure(microscope: 'Microscope') -> Generator:
        """
        Plan for optimizing exposure time.
        
        Parameters
        ----------
        microscope : Microscope
            The microscope instance to optimize exposure for
            
        Yields
        ------
        Generator
            Bluesky plan messages
        """
        yield from microscope.hardware.auto_exposure()

class Microscope:
    """Main microscope interface combining hardware and experiment control."""
    
    def __init__(self, mmc):
        self.hardware = MicroscopeHardware(mmc)
        self.experiment = ExperimentController(self.hardware)
        self.plans = Plans()

    def grid_scan(self, *args, **kwargs) -> Generator:
        """Convenience method to run a grid scan plan."""
        return Plans.grid_scan(self, *args, **kwargs)
    
    def auto_focus(self) -> Generator:
        """Convenience method to run auto-focus plan."""
        return Plans.auto_focus(self)
    
    def auto_exposure(self) -> Generator:
        """Convenience method to run auto-exposure plan."""
        return Plans.auto_exposure(self)

    def _generate_scan_positions(self, 
                               grid: Optional[Tuple[int, int]], 
                               num: int, 
                               start_pos: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generate scanning positions based on parameters."""
        if grid is not None:
            rows, cols = grid
            # Generate grid positions
            positions = []
            for i in range(rows):
                for j in range(cols):
                    x = start_pos[0] + j * self.hardware.estimate_axial_length()
                    y = start_pos[1] + i * self.hardware.estimate_axial_length()
                    positions.append((x, y))
            return positions
        else:
            # Use the existing grid generation logic for num points
            grid_spec = self.hardware.generate_grid(*start_pos, num=num)
            return [(p['x'], p['y']) for p in grid_spec.midpoints()]

def inspect_plan(plan):
    msgs = list(plan)
    for m in msgs:
        print(m)
