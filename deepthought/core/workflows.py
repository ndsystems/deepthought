"""
High-level microscopy workflows built on the action-perception loop.

This module provides ready-to-use workflows for common microscopy experiments,
combining strategies into coherent experimental protocols.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional, Set, Tuple

from ..domain.biology import BiologicalEntity, EntityType
from .loop import (
    MicroscopeState,
    Perception,
    StagePosition
)
from .strategies import (
    CompositeStrategy,
    FocusMapStrategy,
    MapSampleStrategy,
    MultiChannelAcquisitionStrategy,
    SampleMappingWorkflow,
    TimeSeriesWorkflow,
    TrackDynamicsStrategy
)

@dataclass
class CellTrackingExperiment:
    """Complete workflow for cell tracking experiment"""
    
    # Experimental parameters
    duration: timedelta
    interval: timedelta
    channels: Dict[str, float]
    target_cell_type: EntityType
    min_cells: int = 10
    
    async def run(self, initial_state: MicroscopeState) -> Perception:
        """Run complete cell tracking experiment"""
        # 1. Initial sample mapping
        mapping = await SampleMappingWorkflow(
            center=initial_state.stage,
            size=(1000, 1000),  # μm
            resolution=100,  # μm
            channels=self.channels
        ).run(initial_state)
        
        # 2. Find cells of interest
        from .strategies import FindCellsStrategy
        cell_finding = FindCellsStrategy(
            cell_type=self.target_cell_type,
            min_count=self.min_cells
        )
        
        # 3. Setup time series tracking
        tracking = TimeSeriesWorkflow(
            channels=self.channels,
            duration=self.duration,
            interval=self.interval,
            positions=[
                StagePosition(**pos)
                for pos in mapping.spatial_context.values()
            ]
        )
        
        # 4. Run complete workflow
        strategy = CompositeStrategy([
            cell_finding,
            tracking
        ])
        
        from .loop import MicroscopyLoop
        loop = MicroscopyLoop(strategy, initial_state)
        return await loop.run()

@dataclass
class TissueMappingExperiment:
    """Complete workflow for tissue mapping"""
    
    # Mapping parameters
    size: Tuple[float, float]  # μm
    resolution: float  # μm
    channels: Dict[str, float]
    focus_range: float = 10.0  # μm
    
    async def run(self, initial_state: MicroscopeState) -> Perception:
        """Run complete tissue mapping experiment"""
        # 1. Create focus map
        focus_map = FocusMapStrategy(
            positions=self._generate_positions(initial_state.stage),
            focus_range=self.focus_range
        )
        
        # 2. Setup mapping
        mapping = MapSampleStrategy(
            center=initial_state.stage,
            size=self.size,
            resolution=self.resolution
        )
        
        # 3. Setup acquisition
        acquisition = MultiChannelAcquisitionStrategy(
            channels=self.channels,
            position=initial_state.stage  # Will be updated by mapping
        )
        
        # 4. Run complete workflow
        strategy = CompositeStrategy([
            focus_map,
            mapping,
            acquisition
        ])
        
        from .loop import MicroscopyLoop
        loop = MicroscopyLoop(strategy, initial_state)
        return await loop.run()
    
    def _generate_positions(self,
                          center: StagePosition
                          ) -> List[StagePosition]:
        """Generate positions for focus map"""
        width, height = self.size
        x_steps = int(width / (self.resolution * 5))  # Coarser for focus map
        y_steps = int(height / (self.resolution * 5))
        
        positions = []
        for i in range(-x_steps//2, x_steps//2 + 1):
            for j in range(-y_steps//2, y_steps//2 + 1):
                x = center.x + (i * self.resolution * 5)
                y = center.y + (j * self.resolution * 5)
                positions.append(StagePosition(x=x, y=y, z=center.z))
        
        return positions

@dataclass
class MultiModalExperiment:
    """Workflow combining multiple imaging modalities"""
    
    # Modality parameters
    brightfield: Dict[str, float]
    fluorescence: Dict[str, float]
    duration: timedelta
    interval: timedelta
    
    async def run(self, initial_state: MicroscopeState) -> Perception:
        """Run multi-modal experiment"""
        # 1. Initial brightfield mapping
        brightfield_mapping = await SampleMappingWorkflow(
            center=initial_state.stage,
            size=(1000, 1000),  # μm
            resolution=100,  # μm
            channels=self.brightfield
        ).run(initial_state)
        
        # 2. Targeted fluorescence acquisition
        fluorescence = MultiChannelAcquisitionStrategy(
            channels=self.fluorescence,
            position=initial_state.stage
        )
        
        # 3. Time series tracking
        tracking = TimeSeriesWorkflow(
            channels={**self.brightfield, **self.fluorescence},
            duration=self.duration,
            interval=self.interval,
            positions=[
                StagePosition(**pos)
                for pos in brightfield_mapping.spatial_context.values()
            ]
        )
        
        # 4. Run complete workflow
        strategy = CompositeStrategy([
            fluorescence,
            tracking
        ])
        
        from .loop import MicroscopyLoop
        loop = MicroscopyLoop(strategy, initial_state)
        return await loop.run()

@dataclass
class AdaptiveImagingExperiment:
    """Workflow that adapts to observed phenomena"""
    
    # Initial parameters
    channels: Dict[str, float]
    duration: timedelta
    
    async def run(self, initial_state: MicroscopeState) -> Perception:
        """Run adaptive experiment"""
        # Start with basic mapping
        mapping = await SampleMappingWorkflow(
            center=initial_state.stage,
            size=(500, 500),  # μm
            resolution=50,  # μm
            channels=self.channels
        ).run(initial_state)
        
        # Analyze results and adapt strategy
        if self._detect_motion(mapping):
            # Switch to tracking strategy
            strategy = TrackDynamicsStrategy(
                duration=self.duration,
                interval=timedelta(seconds=30),
                target_entities=set(mapping.entities.keys())
            )
        else:
            # Switch to high-resolution mapping
            strategy = MapSampleStrategy(
                center=initial_state.stage,
                size=(200, 200),  # μm
                resolution=10,  # μm
            )
        
        # Run adapted workflow
        from .loop import MicroscopyLoop
        loop = MicroscopyLoop(strategy, initial_state)
        return await loop.run()
    
    def _detect_motion(self, perception: Perception) -> bool:
        """Analyze perception for signs of motion"""
        # Implementation would detect dynamic behavior
        return False
