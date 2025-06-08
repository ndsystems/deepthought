"""Bluesky plans for microscopy actions.

These plans implement the atomic actions for our action-perception loop.
Each plan does one thing well and returns structured data to the RunEngine.
"""

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky import Msg
import numpy as np
from typing import Dict, List, Optional, Tuple, Generator


def move_stage(stage, x: float, y: float) -> Generator[Msg, None, None]:
    """Move microscope stage to absolute position.
    
    Args:
        stage: Ophyd stage device  
        x: Target X position in microns
        y: Target Y position in microns
        
    Yields:
        Bluesky messages for stage movement
    """
    yield from bps.mov(stage, [x, y])


def set_focus(focus, z: float) -> Generator[Msg, None, None]:
    """Set microscope focus to absolute Z position.
    
    Args:
        focus: Ophyd focus device
        z: Target Z position in microns
        
    Yields:
        Bluesky messages for focus adjustment
    """
    yield from bps.mov(focus, z)


def set_exposure(camera, exposure_ms: float) -> Generator[Msg, None, None]:
    """Set camera exposure time.
    
    Args:
        camera: Ophyd camera device
        exposure_ms: Exposure time in milliseconds
        
    Yields:
        Bluesky messages for exposure setting
    """
    yield from bps.mov(camera.exposure, exposure_ms)


def acquire_image(camera, channel=None) -> Generator[Msg, None, None]:
    """Acquire single image from camera.
    
    Args:
        camera: Ophyd camera device
        channel: Optional channel/illumination setting
        
    Yields:
        Bluesky messages for image acquisition
    """
    if channel is not None:
        yield from bps.mov(channel, "on")  # or appropriate channel setting
    
    # Wrap in run for proper data collection
    @bpp.run_decorator()
    def inner():
        yield from bps.trigger_and_read([camera])
    
    yield from inner()


def autofocus(focus, camera, range_um: float = 10.0, steps: int = 20) -> Generator[Msg, None, None]:
    """Perform autofocus using focus sweep.
    
    Args:
        focus: Ophyd focus device
        camera: Ophyd camera device  
        range_um: Focus range to search in microns
        steps: Number of focus steps to try
        
    Yields:
        Bluesky messages for autofocus routine
    """
    # Get current focus position
    current_z = yield from bps.rd(focus)
    start_z = current_z - range_um / 2
    end_z = current_z + range_um / 2
    
    best_z = current_z
    best_score = 0
    
    # Sweep through focus positions
    for z in np.linspace(start_z, end_z, steps):
        yield from bps.mov(focus, z)
        reading = yield from bps.trigger_and_read([camera])
        
        # Calculate focus score (would need image analysis)
        # For now, placeholder - actual implementation would analyze image sharpness
        focus_score = _calculate_focus_score(reading)
        
        if focus_score > best_score:
            best_score = focus_score
            best_z = z
    
    # Move to best focus position
    yield from bps.mov(focus, best_z)


def scan_xy_grid(stage_x, stage_y, camera, center: Tuple[float, float], 
                 size: Tuple[float, float], step: float) -> Generator[Msg, None, None]:
    """Scan XY grid and acquire images at each position.
    
    Args:
        stage_x: Ophyd X-axis device
        stage_y: Ophyd Y-axis device  
        camera: Ophyd camera device
        center: (x, y) center position in microns
        size: (width, height) scan area in microns  
        step: Step size between positions in microns
        
    Yields:
        Bluesky messages for grid scan
    """
    x_center, y_center = center
    width, height = size
    
    x_start = x_center - width / 2
    x_end = x_center + width / 2
    y_start = y_center - height / 2 
    y_end = y_center + height / 2
    
    x_positions = np.arange(x_start, x_end + step, step)
    y_positions = np.arange(y_start, y_end + step, step)
    
    @bpp.run_decorator()
    def inner():
        for x in x_positions:
            for y in y_positions:
                yield from bps.mov(stage_x, x, stage_y, y)
                yield from bps.trigger_and_read([camera, stage_x, stage_y])
    
    yield from inner()


def multi_channel_acquisition(devices: Dict, channels: List[str], 
                             exposure_times: Dict[str, float]) -> Generator[Msg, None, None]:
    """Acquire images across multiple channels.
    
    Args:
        devices: Dict with 'camera', 'channel', etc.
        channels: List of channel names to acquire
        exposure_times: Dict mapping channel names to exposure times
        
    Yields:
        Bluesky messages for multi-channel acquisition
    """
    camera = devices['camera']
    channel_device = devices.get('channel')
    
    @bpp.run_decorator()
    def inner():
        for ch in channels:
            # Switch to channel
            if channel_device is not None:
                yield from bps.mov(channel_device, ch)
            
            # Acquire image
            yield from bps.trigger_and_read([camera])
    
    yield from inner()


def time_series(devices: Dict, channels: List[str], 
                num_timepoints: int, interval: float) -> Generator[Msg, None, None]:
    """Acquire time series across multiple channels.
    
    Args:
        devices: Dict with microscope devices
        channels: List of channels to acquire
        num_timepoints: Number of time points
        interval: Time interval between acquisitions in seconds
        
    Yields:
        Bluesky messages for time series acquisition
    """
    camera = devices['camera']
    channel_device = devices.get('channel')
    
    @bpp.run_decorator()
    def inner():
        for timepoint in range(num_timepoints):
            # Acquire all channels at this timepoint
            for ch in channels:
                if channel_device is not None:
                    yield from bps.mov(channel_device, ch)
                yield from bps.trigger_and_read([camera])
            
            # Wait for next timepoint (except on last one)
            if timepoint < num_timepoints - 1:
                yield from bps.sleep(interval)
    
    yield from inner()


def z_stack(focus, camera, start_z: float, end_z: float, 
            step_z: float) -> Generator[Msg, None, None]:
    """Acquire Z-stack of images.
    
    Args:
        focus: Ophyd focus device
        camera: Ophyd camera device
        start_z: Starting Z position in microns
        end_z: Ending Z position in microns  
        step_z: Step size in microns
        
    Yields:
        Bluesky messages for Z-stack acquisition
    """
    z_positions = np.arange(start_z, end_z + step_z, step_z)
    
    @bpp.run_decorator()
    def inner():
        for z in z_positions:
            yield from bps.mov(focus, z)
            yield from bps.trigger_and_read([camera, focus])
    
    yield from inner()


def find_sample_surface(focus, camera, search_range: float = 100.0,
                       coarse_step: float = 10.0, fine_step: float = 1.0) -> Generator[Msg, None, None]:
    """Find sample surface using two-stage focus search.
    
    Args:
        focus: Ophyd focus device
        camera: Ophyd camera device
        search_range: Total search range in microns
        coarse_step: Coarse search step size
        fine_step: Fine search step size
        
    Yields:
        Bluesky messages for surface finding
    """
    # Get starting position
    start_z = yield from bps.rd(focus)
    
    # Coarse search
    best_z_coarse = yield from _focus_search(
        focus, camera, start_z, search_range, coarse_step
    )
    
    # Fine search around best coarse position
    fine_range = coarse_step * 2
    best_z_fine = yield from _focus_search(
        focus, camera, best_z_coarse, fine_range, fine_step
    )
    
    # Move to final position
    yield from bps.mov(focus, best_z_fine)


def _focus_search(focus, camera, center_z: float, range_um: float, 
                 step: float) -> Generator[Msg, None, None]:
    """Helper function for focus searching."""
    start_z = center_z - range_um / 2
    end_z = center_z + range_um / 2
    
    best_z = center_z
    best_score = 0
    
    for z in np.arange(start_z, end_z + step, step):
        yield from bps.mov(focus, z)
        reading = yield from bps.trigger_and_read([camera])
        
        focus_score = _calculate_focus_score(reading)
        if focus_score > best_score:
            best_score = focus_score
            best_z = z
    
    return best_z


def _calculate_focus_score(reading: Dict) -> float:
    """Calculate focus score from camera reading.
    
    This is a placeholder - actual implementation would analyze
    image sharpness using gradient variance or similar metrics.
    """
    # Placeholder implementation
    return np.random.random()


# Higher-level composite plans

@bpp.stage_decorator([])  # Add devices to stage as needed
def complete_position_acquisition(devices: Dict, position: Tuple[float, float],
                                 channels: List[str], 
                                 exposure_times: Dict[str, float]) -> Generator[Msg, None, None]:
    """Complete acquisition workflow at a single position.
    
    Args:
        devices: Dict with all microscope devices
        position: (x, y) stage position
        channels: List of channels to acquire
        exposure_times: Exposure times per channel
        
    Yields:
        Bluesky messages for complete position acquisition
    """
    stage = devices['stage']
    focus = devices['focus'] 
    camera = devices['camera']
    
    # Move to position
    yield from move_stage(stage, *position)
    
    # Find focus
    yield from find_sample_surface(focus, camera)
    
    # Acquire all channels
    yield from multi_channel_acquisition(devices, channels, exposure_times)


@bpp.stage_decorator([])
def adaptive_grid_scan(devices: Dict, initial_positions: List[Tuple[float, float]],
                      channels: List[str], quality_threshold: float = 0.5) -> Generator[Msg, None, None]:
    """Adaptive grid scan that adds positions based on quality metrics.
    
    Args:
        devices: Dict with microscope devices
        initial_positions: Starting grid positions
        channels: Channels to acquire
        quality_threshold: Minimum quality to accept position
        
    Yields:
        Bluesky messages for adaptive scanning
    """
    positions_to_scan = list(initial_positions)
    positions_scanned = []
    
    while positions_to_scan:
        position = positions_to_scan.pop(0)
        
        # Acquire at this position
        yield from complete_position_acquisition(
            devices, position, channels, {}
        )
        
        # Analyze quality (placeholder)
        quality = _assess_position_quality()
        
        if quality < quality_threshold:
            # Add neighboring positions for better sampling
            neighbors = _generate_neighbor_positions(position, step=50.0)
            positions_to_scan.extend(neighbors)
        
        positions_scanned.append(position)


def _assess_position_quality() -> float:
    """Placeholder for position quality assessment."""
    return np.random.random()


def _generate_neighbor_positions(center: Tuple[float, float], 
                               step: float) -> List[Tuple[float, float]]:
    """Generate neighboring positions around a center point."""
    x, y = center
    neighbors = [
        (x - step, y), (x + step, y),
        (x, y - step), (x, y + step)
    ]
    return neighbors