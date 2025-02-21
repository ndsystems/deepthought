"""
Main entry point for microscope automation system using action-perception loop.
Configures and runs microscope experiments with multiple channels.
"""

from typing import Dict, List, Optional, Tuple
import asyncio
import numpy as np
import napari
from datetime import datetime, timedelta

from microscope import ActionPerceptionMicroscope
from devices import MMCoreInterface
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine
from data import db
from detection import NuclearDetector
from channels import ChannelConfig

from .microscopy_loop import (
    MicroscopeAction,
    MicroscopeState,
    ObservationStrategy,
    Perception,
    StagePosition
)
from .microscopy_strategies import (
    CompositeStrategy,
    MapSampleStrategy,
    MultiChannelAcquisitionStrategy
)
from .microscopy_workflows import (
    CellTrackingExperiment,
    TissueMappingExperiment
)

class ActionPerceptionViewer:
    """Viewer for action-perception loop progress"""
    
    def __init__(self):
        self.viewer = napari.Viewer()
        self.layers = {}
        
    def update_perception(self, perception: Perception):
        """Update display with current perception"""
        # Update cell positions
        cells = perception.get_entities(type="cell")
        self._update_cell_layer(cells)
        
        # Update current field of view
        fov = perception.get_field_of_view()
        self._update_fov_layer(fov)
        
        # Update quality metrics
        self._update_quality_layer(perception.quality_metrics)
        
    def _update_cell_layer(self, cells: List[BiologicalEntity]):
        """Update cell positions"""
        positions = [cell.position for cell in cells]
        if 'cells' not in self.layers:
            self.layers['cells'] = self.viewer.add_points(
                positions,
                name='Detected Cells',
                size=10,
                face_color='red'
            )
        else:
            self.layers['cells'].data = positions
            
    def _update_fov_layer(self, fov: Dict[str, float]):
        """Update field of view rectangle"""
        if not fov:
            return
            
        rect = np.array([
            [fov['x'] - fov['width']/2, fov['y'] - fov['height']/2],
            [fov['x'] + fov['width']/2, fov['y'] + fov['height']/2]
        ])
        
        if 'fov' not in self.layers:
            self.layers['fov'] = self.viewer.add_shapes(
                rect,
                shape_type='rectangle',
                name='Field of View',
                edge_color='yellow',
                face_color='transparent'
            )
        else:
            self.layers['fov'].data = rect
            
    def _update_quality_layer(self, metrics: Dict[str, float]):
        """Update quality metrics display"""
        if not metrics:
            return
            
        if 'quality' not in self.layers:
            self.layers['quality'] = self.viewer.add_points(
                [],
                name='Quality Metrics',
                size=5,
                face_color='blue'
            )
        
        positions = []
        colors = []
        for pos_str, quality in metrics.items():
            x, y, z = eval(pos_str)  # Convert string position to coordinates
            positions.append([x, y])
            colors.append([0, 0, quality])  # Blue channel intensity shows quality
            
        self.layers['quality'].data = positions
        self.layers['quality'].face_color = colors

class ExperimentConfig:
    """Configuration for microscopy experiments"""
    
    def __init__(self):
        self.region_size = (500, 500)  # μm
        self.min_cells = 100
        self.max_time = 3600  # seconds
        self.channels = setup_channels()
        
    def create_strategy(self) -> ObservationStrategy:
        """Create appropriate strategy based on config"""
        mapping = MapSampleStrategy(
            center=StagePosition(x=0, y=0, z=0),
            size=self.region_size,
            resolution=10  # μm
        )
        
        acquisition = MultiChannelAcquisitionStrategy(
            channels={ch.name: ch.exposure for ch in self.channels},
            position=StagePosition(x=0, y=0, z=0)
        )
        
        return CompositeStrategy([mapping, acquisition])

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
    
    return RE

class ActionPerceptionBlueskyBridge:
    """Bridge between action-perception loop and Bluesky"""
    
    def __init__(self, RE: RunEngine):
        self.RE = RE
        self.current_run = None
        
    async def start_experiment(self, config: ExperimentConfig):
        """Start new experiment run"""
        # Create metadata for the run
        md = {
            'experiment': config.__class__.__name__,
            'region_size': config.region_size,
            'channels': [ch.name for ch in config.channels],
            'start_time': datetime.now().isoformat()
        }
        
        # Start new run
        self.current_run = await self.RE.open_run(metadata=md)
        
    async def log_action(self, action: MicroscopeAction, result: Dict):
        """Log action and its result to Bluesky"""
        if not self.current_run:
            return
            
        # Create document for the action
        doc = {
            'action_type': action.__class__.__name__,
            'timestamp': datetime.now().isoformat(),
            'parameters': action.__dict__,
            'result': result
        }
        
        # Save to database
        await self.current_run.save('action', doc)
        
    async def log_perception(self, perception: Perception):
        """Log current perception state to Bluesky"""
        if not self.current_run:
            return
            
        # Create document for perception update
        doc = {
            'timestamp': datetime.now().isoformat(),
            'entities': [e.__dict__ for e in perception.entities.values()],
            'quality_metrics': perception.quality_metrics,
            'spatial_context': perception.spatial_context
        }
        
        # Save to database
        await self.current_run.save('perception', doc)
        
    async def end_experiment(self):
        """End current experiment run"""
        if self.current_run:
            await self.current_run.close()
            self.current_run = None

async def run_experiment(config: ExperimentConfig, microscope: ActionPerceptionMicroscope):
    """Run experiment with real-time visualization and Bluesky integration"""
    # Setup viewer and Bluesky
    viewer = ActionPerceptionViewer()
    RE = configure_run_engine()
    bridge = ActionPerceptionBlueskyBridge(RE)
    
    # Create initial microscope state
    initial_state = MicroscopeState(
        stage=StagePosition(x=0, y=0, z=0),
        objective="10x",
        channel="DAPI"
    )
    
    # Create experiment based on config
    if config.min_cells > 0:
        experiment = CellTrackingExperiment(
            duration=timedelta(seconds=config.max_time),
            interval=timedelta(seconds=30),
            channels={ch.name: ch.exposure for ch in config.channels},
            target_cell_type="cell",
            min_cells=config.min_cells
        )
    else:
        experiment = TissueMappingExperiment(
            size=config.region_size,
            resolution=10,  # μm
            channels={ch.name: ch.exposure for ch in config.channels}
        )
    
    # Start Bluesky run
    await bridge.start_experiment(config)
    
    # Run experiment with visualization and Bluesky updates
    async def update_state(action: MicroscopeAction, result: Dict, perception: Perception):
        # Update viewer
        viewer.update_perception(perception)
        
        # Log to Bluesky
        await bridge.log_action(action, result)
        await bridge.log_perception(perception)
        
        await asyncio.sleep(0.1)  # Don't update too frequently
    
    # Run experiment
    try:
        results = await experiment.run(
            initial_state=initial_state,
            callback=update_state
        )
        return results
    finally:
        await microscope.cleanup()
        await bridge.end_experiment()

def main():
    """Main execution function."""
    # Setup hardware and software components
    scopes = setup_microscopes()
    config = ExperimentConfig()
    
    # Initialize microscope with action-perception capabilities
    microscope = ActionPerceptionMicroscope(
        mmc=scopes["bright_star"],
        channels=config.channels
    )
    
    # Run experiment
    asyncio.run(run_experiment(config, microscope))

if __name__ == "__main__":
    main()
