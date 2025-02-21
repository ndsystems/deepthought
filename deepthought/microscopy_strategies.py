"""
Microscopy observation strategies and workflows.

This module implements concrete strategies for common microscopy workflows,
built on the action-perception loop architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from .biology import BiologicalEntity, EntityType
from .microscopy_loop import (
    ActionContext,
    ActionResult,
    AcquireImage,
    AutoFocus,
    MoveStageTo,
    MicroscopeAction,
    MicroscopeState,
    ObservationStrategy,
    Perception,
    StagePosition
)

class CompositeStrategy(ObservationStrategy):
    """Strategy that combines multiple sub-strategies"""
    
    def __init__(self, strategies: List[ObservationStrategy]):
        self.strategies = strategies
        self.current_index = 0
    
    def next_action(self, perception: Perception) -> Optional[MicroscopeAction]:
        """Get next action from current strategy"""
        while self.current_index < len(self.strategies):
            strategy = self.strategies[self.current_index]
            action = strategy.next_action(perception)
            
            if action is not None:
                return action
            
            # Current strategy complete, move to next
            self.current_index += 1
        
        return None
    
    def is_complete(self, perception: Perception) -> bool:
        """Check if all strategies are complete"""
        return self.current_index >= len(self.strategies)

class TrackDynamicsStrategy(ObservationStrategy):
    """Strategy for tracking dynamic processes"""
    
    def __init__(self,
                 duration: timedelta,
                 interval: timedelta,
                 target_entities: Set[str]):
        self.start_time = datetime.now()
        self.end_time = self.start_time + duration
        self.interval = interval
        self.target_entities = target_entities
        self.last_observation = {}
        self.next_observation = {}
        
        # Initialize observation schedule
        for entity_id in target_entities:
            self.next_observation[entity_id] = self.start_time
    
    def next_action(self, perception: Perception) -> Optional[MicroscopeAction]:
        """Get next action based on observation schedule"""
        now = datetime.now()
        
        # Find entities due for observation
        due_entities = [
            eid for eid, next_time in self.next_observation.items()
            if now >= next_time
        ]
        
        if due_entities:
            entity_id = due_entities[0]
            if entity_id in perception.spatial_context:
                # Move to last known position
                pos = perception.spatial_context[entity_id]
                return MoveStageTo(StagePosition(**pos))
            else:
                # Entity lost, would need search strategy
                return None
        
        return None
    
    def is_complete(self, perception: Perception) -> bool:
        """Check if tracking duration is complete"""
        return datetime.now() >= self.end_time

class MapSampleStrategy(ObservationStrategy):
    """Strategy for mapping sample region"""
    
    def __init__(self,
                 center: StagePosition,
                 size: Tuple[float, float],
                 resolution: float):
        self.center = center
        self.size = size
        self.resolution = resolution
        self.positions = self._generate_positions()
        self.visited = set()
        self.quality_threshold = 0.7
    
    def next_action(self, perception: Perception) -> Optional[MicroscopeAction]:
        """Get next mapping action"""
        # Find unvisited positions
        remaining = [
            pos for pos in self.positions
            if pos not in self.visited
        ]
        
        if not remaining:
            return None
        
        # Get next position
        next_pos = remaining[0]
        
        # Check if we need to revisit any low quality positions
        low_quality = [
            pos for pos in self.visited
            if perception.quality_metrics.get(str(pos), 0) < self.quality_threshold
        ]
        
        if low_quality:
            next_pos = low_quality[0]
        
        return MoveStageTo(next_pos)
    
    def is_complete(self, perception: Perception) -> bool:
        """Check if mapping is complete with good quality"""
        if len(self.visited) < len(self.positions):
            return False
        
        # Check quality metrics
        qualities = [
            perception.quality_metrics.get(str(pos), 0)
            for pos in self.positions
        ]
        return min(qualities, default=0) >= self.quality_threshold
    
    def _generate_positions(self) -> List[StagePosition]:
        """Generate grid of positions to map"""
        width, height = self.size
        x_steps = int(width / self.resolution)
        y_steps = int(height / self.resolution)
        
        positions = []
        for i in range(-x_steps//2, x_steps//2 + 1):
            for j in range(-y_steps//2, y_steps//2 + 1):
                x = self.center.x + (i * self.resolution)
                y = self.center.y + (j * self.resolution)
                positions.append(StagePosition(x=x, y=y, z=self.center.z))
        
        return positions

class FocusMapStrategy(ObservationStrategy):
    """Strategy for creating focus map"""
    
    def __init__(self,
                 positions: List[StagePosition],
                 focus_range: float = 10.0):
        self.positions = positions
        self.focus_range = focus_range
        self.focus_map = {}
        self.current_position = None
    
    def next_action(self, perception: Perception) -> Optional[MicroscopeAction]:
        """Get next focus mapping action"""
        # If we're at a position, do autofocus
        if self.current_position:
            if str(self.current_position) not in self.focus_map:
                return AutoFocus(range_um=self.focus_range)
            else:
                self.current_position = None
        
        # Move to next unmapped position
        for pos in self.positions:
            if str(pos) not in self.focus_map:
                self.current_position = pos
                return MoveStageTo(pos)
        
        return None
    
    def is_complete(self, perception: Perception) -> bool:
        """Check if focus map is complete"""
        return len(self.focus_map) == len(self.positions)

class MultiChannelAcquisitionStrategy(ObservationStrategy):
    """Strategy for multi-channel acquisition"""
    
    def __init__(self,
                 channels: Dict[str, float],  # channel -> exposure
                 position: StagePosition):
        self.channels = channels
        self.position = position
        self.acquired = set()
    
    def next_action(self, perception: Perception) -> Optional[MicroscopeAction]:
        """Get next acquisition action"""
        # First ensure we're at the right position
        if not self._at_position(perception):
            return MoveStageTo(self.position)
        
        # Find next channel to acquire
        for channel, exposure in self.channels.items():
            if channel not in self.acquired:
                return AcquireImage(exposure=exposure, channel=channel)
        
        return None
    
    def is_complete(self, perception: Perception) -> bool:
        """Check if all channels acquired"""
        return len(self.acquired) == len(self.channels)
    
    def _at_position(self, perception: Perception) -> bool:
        """Check if we're at the target position"""
        current = perception.spatial_context.get('current_position')
        if not current:
            return False
        
        return (abs(current.x - self.position.x) < 0.1 and
                abs(current.y - self.position.y) < 0.1 and
                abs(current.z - self.position.z) < 0.1)

@dataclass
class TimeSeriesWorkflow:
    """Workflow for time series acquisition"""
    
    channels: Dict[str, float]
    duration: timedelta
    interval: timedelta
    positions: List[StagePosition]
    
    async def run(self, initial_state: MicroscopeState):
        """Run time series workflow"""
        # Create strategies for each position
        position_strategies = []
        for pos in self.positions:
            acquisition = MultiChannelAcquisitionStrategy(
                channels=self.channels,
                position=pos
            )
            focus_map = FocusMapStrategy(
                positions=[pos],
                focus_range=10.0
            )
            position_strategies.append(CompositeStrategy([
                focus_map,
                acquisition
            ]))
        
        # Create tracking strategy
        tracking = TrackDynamicsStrategy(
            duration=self.duration,
            interval=self.interval,
            target_entities=set()  # Will be populated as we find entities
        )
        
        # Combine strategies
        strategy = CompositeStrategy([
            CompositeStrategy(position_strategies),
            tracking
        ])
        
        # Run microscopy loop
        from .microscopy_loop import MicroscopyLoop
        loop = MicroscopyLoop(strategy, initial_state)
        return await loop.run()

@dataclass
class SampleMappingWorkflow:
    """Workflow for mapping sample"""
    
    center: StagePosition
    size: Tuple[float, float]
    resolution: float
    channels: Dict[str, float]
    
    async def run(self, initial_state: MicroscopeState):
        """Run sample mapping workflow"""
        # Create mapping strategy
        mapping = MapSampleStrategy(
            center=self.center,
            size=self.size,
            resolution=self.resolution
        )
        
        # Create acquisition strategy
        acquisition = MultiChannelAcquisitionStrategy(
            channels=self.channels,
            position=self.center  # Will be updated by mapping
        )
        
        # Combine strategies
        strategy = CompositeStrategy([mapping, acquisition])
        
        # Run microscopy loop
        from .microscopy_loop import MicroscopyLoop
        loop = MicroscopyLoop(strategy, initial_state)
        return await loop.run()
