"""Bluesky execution infrastructure for microscopy plans.

Provides RunEngine setup and execution context for our action-perception loop.
"""

from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from databroker import Broker
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional
import logging


class MicroscopyRunEngine:
    """RunEngine configured for microscopy workflows."""
    
    def __init__(self, enable_plots: bool = False, enable_table: bool = True):
        """
        Args:
            enable_plots: Enable live plotting during acquisition
            enable_table: Enable live table output
        """
        # Create RunEngine
        self.RE = RunEngine({})
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Setup callbacks
        self._setup_callbacks(enable_plots, enable_table)
        
        # Setup data broker (optional)
        self._setup_databroker()
        
    def _setup_callbacks(self, enable_plots: bool, enable_table: bool):
        """Setup standard callbacks for data collection."""
        # Best effort callback for live feedback
        self.bec = BestEffortCallback()
        
        if not enable_plots:
            self.bec.disable_plots()
        if not enable_table:
            self.bec.disable_table()
            
        self.RE.subscribe(self.bec)
        
    def _setup_databroker(self):
        """Setup databroker for data storage (optional)."""
        try:
            # For production, you'd use persistent storage like:
            # from databroker import catalog  
            # self.db = catalog['your_catalog_name']
            
            # For now, create in-memory databroker for testing
            self.db = Broker.named('temp')
            self.RE.subscribe(self.db.insert)
            self.logger.info("Databroker connected (in-memory)")
        except Exception as e:
            self.logger.warning(f"Databroker setup failed: {e}")
            self.db = None
            
    def get_run_data(self, scan_id):
        """Retrieve data from a completed scan."""
        if self.db is None:
            return None
        try:
            # Get the run by scan_id
            run = self.db[scan_id]
            return run.primary.read()
        except Exception as e:
            self.logger.error(f"Failed to retrieve data for scan {scan_id}: {e}")
            return None
            
    def list_recent_scans(self, n=10):
        """List recent scans with metadata."""
        if self.db is None:
            return []
        try:
            scans = []
            for run in list(self.db())[:n]:
                scans.append({
                    'scan_id': run.metadata['start']['scan_id'],
                    'uid': run.metadata['start']['uid'][:8],
                    'plan_name': run.metadata['start'].get('plan_name', 'unknown'),
                    'time': run.metadata['start']['time']
                })
            return scans
        except Exception as e:
            self.logger.error(f"Failed to list scans: {e}")
            return []
    
    def execute(self, plan, metadata: Optional[Dict[str, Any]] = None):
        """Execute a plan with optional metadata.
        
        Args:
            plan: Bluesky plan generator
            metadata: Optional metadata to attach to run
            
        Returns:
            List of run UIDs
        """
        if metadata:
            return self.RE(plan, **metadata)
        else:
            return self.RE(plan)
    
    def abort(self):
        """Abort current plan execution."""
        self.RE.abort()
        
    def stop(self):
        """Stop current plan execution gracefully."""
        self.RE.stop()
        
    def pause(self):
        """Pause current plan execution."""
        self.RE.request_pause()
        
    def resume(self):
        """Resume paused plan execution."""
        self.RE.resume()
    
    @property
    def state(self):
        """Get current RunEngine state."""
        return self.RE.state
        
    def summary(self):
        """Get execution summary."""
        return {
            'state': self.state,
            'runs_completed': len(self.RE.call_returns) if hasattr(self.RE, 'call_returns') else 0,
            'databroker_connected': self.db is not None
        }


def create_mock_devices():
    """Create mock devices for testing plans."""
    from ophyd.sim import SynAxis, SynSignal
    
    # Mock stage - use separate x,y axes
    stage_x = SynAxis(name='stage_x')
    stage_y = SynAxis(name='stage_y')
    
    # Mock focus
    focus = SynAxis(name='focus_z', value=0)
    
    # Mock camera with exposure - use proper ophyd device
    from ophyd.sim import noisy_det
    camera = noisy_det
    
    # Mock channel - use SynSignal directly
    channel = SynSignal(name='channel')
    
    return {
        'stage_x': stage_x,
        'stage_y': stage_y,
        'focus': focus,
        'camera': camera,
        'channel': channel
    }


def test_plans_with_mocks():
    """Test our plans with mock devices."""
    import time
    import sys
    import os
    
    # Add the current directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    
    # Import plans directly to avoid import cascade
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'hardware'))
    from plans import (
        move_stage, set_focus, acquire_image, 
        scan_xy_grid, multi_channel_acquisition, time_series, z_stack
    )
    import bluesky.plan_stubs as bps
    import bluesky.preprocessors as bpp
    
    print("Creating mock devices...")
    devices = create_mock_devices()
    
    print("Setting up RunEngine...")
    microscope_re = MicroscopyRunEngine(enable_plots=False)
    
    print("\n=== Testing Basic Plans ===")
    
    # Test individual axis movement
    print("Testing stage X movement...")
    microscope_re.execute(set_focus(devices['stage_x'], 100))
    print(f"Stage X position: {devices['stage_x'].read()}")
    
    print("Testing stage Y movement...")
    microscope_re.execute(set_focus(devices['stage_y'], 200))
    print(f"Stage Y position: {devices['stage_y'].read()}")
    
    # Test focus
    print("Testing focus...")
    microscope_re.execute(set_focus(devices['focus'], 50))
    print(f"Focus position: {devices['focus'].read()}")
    
    # Test image acquisition
    print("Testing image acquisition...")
    microscope_re.execute(acquire_image(devices['camera']))
    print("Image acquired successfully")
    
    print("Basic tests completed - ophyd devices work!")
    
    print("\n=== Testing Complex Workflows ===")
    
    # Test grid scan workflow
    print("Testing 2x2 grid scan...")
    microscope_re.execute(
        scan_xy_grid(
            devices['stage_x'], devices['stage_y'], 
            devices['camera'],
            center=(0, 0),
            size=(100, 100), 
            step=50
        )
    )
    print("Grid scan completed")
    
    # Test multi-channel workflow  
    print("Testing multi-channel acquisition...")
    microscope_re.execute(
        multi_channel_acquisition(
            devices,
            channels=['brightfield', 'dapi'],
            exposure_times={'brightfield': 50, 'dapi': 200}
        )
    )
    print("Multi-channel completed")
    
    # Test time series
    print("Testing time series (3 timepoints, 1s interval)...")
    microscope_re.execute(
        time_series(
            devices,
            channels=['brightfield'],
            num_timepoints=3,
            interval=1.0
        )
    )
    print("Time series completed")
    
    # Test Z-stack workflow
    print("Testing Z-stack (5 slices, 2μm steps)...")
    microscope_re.execute(
        z_stack(
            devices['focus'],
            devices['camera'],
            start_z=0,
            end_z=8,
            step_z=2
        )
    )
    print("Z-stack completed")
    
    # Test composite workflow (grid + multi-channel)
    print("Testing composite workflow: grid scan with multi-channel...")
    
    # Create a composite plan
    @bpp.run_decorator()
    def grid_multichannel():
        # For each grid position, acquire multiple channels
        x_positions = [-25, 0, 25]
        y_positions = [-25, 0, 25]
        channels = ['brightfield', 'dapi']
        
        for x in x_positions:
            for y in y_positions:
                # Move to position
                yield from bps.mov(devices['stage_x'], x, devices['stage_y'], y)
                
                # Acquire all channels at this position
                for ch in channels:
                    yield from bps.mov(devices['channel'], ch)
                    yield from bps.trigger_and_read([devices['camera'], devices['stage_x'], devices['stage_y']])
    
    microscope_re.execute(grid_multichannel())
    print("Composite workflow completed")
    
    print(f"\nRunEngine summary: {microscope_re.summary()}")
    
    # Demonstrate data retrieval
    print("\n=== Data Storage Demonstration ===")
    recent_scans = microscope_re.list_recent_scans(5)
    print("Recent scans:")
    for scan in recent_scans:
        print(f"  Scan {scan['scan_id']}: {scan['plan_name']} (uid: {scan['uid']})")
    
    # Retrieve data from the grid scan (scan 2)
    if len(recent_scans) >= 2:
        grid_data = microscope_re.get_run_data(-4)  # Grid scan was 4th from end
        if grid_data is not None:
            print(f"\nGrid scan data shape: {grid_data['noisy_det'].shape}")
            print(f"Stage X positions: {grid_data['stage_x'][:3]}...")  # First 3 positions
    
    return microscope_re, devices


if __name__ == "__main__":
    # Run tests
    re, devices = test_plans_with_mocks()
    print("All tests completed successfully!")