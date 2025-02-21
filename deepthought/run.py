"""
Main entry point for microscope automation system.
Configures and runs microscope experiments with multiple channels.
"""

from typing import List, Optional, Tuple
import numpy as np
import napari

from microscope import Microscope
from devices import MMCoreInterface
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine
from data import db
from detection import NuclearDetector
from channels import ChannelConfig

class NapariLiveCallback:
    """Callback to display live images in napari viewer."""
    def __init__(self):
        self.viewer = napari.Viewer()
        self.image_layer = None

    def __call__(self, name, doc):
        if doc['name'] != 'primary':
            return
        
        if name == 'descriptor':
            # Initialize viewer on first image
            return
            
        if name == 'event' and 'image' in doc['data']:
            image = doc['data']['image']
            if self.image_layer is None:
                self.image_layer = self.viewer.add_image(image, name='Live View')
            else:
                self.image_layer.data = image

def configure_run_engine(enable_live_view: bool = False) -> RunEngine:
    """
    Configure and initialize the Bluesky RunEngine with callbacks.
    
    Args:
        enable_live_view: If True, displays live images in napari viewer
    """
    # Initialize BestEffortCallback without plots
    bec = BestEffortCallback()
    bec.disable_plots()

    # Create and configure RunEngine
    RE = RunEngine({})
    RE.subscribe(bec)
    RE.subscribe(db.insert)
    
    if enable_live_view:
        live_viewer = NapariLiveCallback()
        RE.subscribe(live_viewer)
    
    return RE

def setup_channels() -> List[ChannelConfig]:
    """Configure imaging channels with their respective settings."""
    # Configure DAPI channel (primary/nuclear)
    dapi = ChannelConfig("DAPI")
    dapi.exposure = 30
    dapi.detector = NuclearDetector()
    dapi.marker = "nuclear"

    # Configure FITC channel (γ-H2AX)
    fitc = ChannelConfig("FITC")
    fitc.exposure = 200
    fitc.detect_with = dapi
    fitc.marker = "g-h2ax"

    # Configure TxRed channel (p-CHK1)
    txred = ChannelConfig("TxRed")
    txred.exposure = 200
    txred.detect_with = dapi
    txred.marker = "p-chk1"

    return [dapi, fitc, txred]

def setup_microscopes() -> MMCoreInterface:
    """Initialize and configure microscope hardware interfaces."""
    scopes = MMCoreInterface()
    
    # Add available microscopes
    scopes.add("10.10.1.35", "bright_star")
    scopes.add("10.10.1.57", "eva_green")
    
    return scopes

def snap_test_image(mmc) -> None:
    """
    Capture and display a test image for debugging purposes.
    
    Args:
        mmc: Microscope MMCore interface
    """
    mmc.snapImage()
    img = np.array(mmc.getImage())
    
    # Display image using napari
    napari.view_image(img)

def main():
    """Main execution function."""
    # Setup hardware and software components
    scopes = setup_microscopes()
    channels = setup_channels()
    RE = configure_run_engine(enable_live_view=True)  # Enable live view

    # Initialize microscope with specific hardware
    microscope = Microscope(mmc=scopes["bright_star"])

    # Configure and run scanning experiment
    initial_coords: Tuple[float, float] = [0, 0]
    scan_plan = microscope.scan_xy(
        channels=channels,
        num=2,
        initial_coords=initial_coords
    )

    # Execute experiment
    RE(scan_plan)

if __name__ == "__main__":
    main()
