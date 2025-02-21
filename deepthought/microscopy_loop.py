"""
Core action-perception loop architecture for microscopy.

This module implements the fundamental action-perception loop that drives
microscopy experiments, matching how microscopists actually work.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Protocol, Set, Tuple
import numpy as np

from .biology import BiologicalEntity, BiologicalSample, EntityType
from .observation import EntityObservation, ObservationSet, TechnicalParameters

class ActionStatus(Enum):
    """Status of an action execution"""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class ActionContext:
    """Context for action execution"""
    microscope_state: 'MicroscopeState'
    technical_params: TechnicalParameters
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

@dataclass
class ActionResult:
    """Result of action execution"""
    status: ActionStatus
    data: Dict
    error: Optional[str] = None
    duration: float = 0.0
    energy_cost: float = 0.0  # Accumulated light exposure

@dataclass
class StagePosition:
    """3D stage position"""
    x: float  # μm
    y: float  # μm
    z: float  # μm

@dataclass
class Objective:
    """Microscope objective properties"""
    magnification: float
    numerical_aperture: float
    working_distance: float  # mm
    is_air: bool = True

@dataclass
class LightPath:
    """Current light path configuration"""
    source: str  # e.g., "brightfield", "488nm_laser"
    intensity: float  # percent
    exposure: float  # ms
    filters: List[str] = field(default_factory=list)

@dataclass
class MicroscopeState:
    """Complete state of microscope system"""
    objective: Objective
    stage: StagePosition
    light_path: LightPath
    temperature: float  # °C
    last_action: Optional[str] = None
    
    def can_execute(self, action: 'MicroscopeAction') -> bool:
        """Check if action is possible in current state"""
        return action.validate(self)
    
    def predict_next_state(self, action: 'MicroscopeAction') -> 'MicroscopeState':
        """Predict state after action execution"""
        return action.predict_state(self)

class MicroscopeAction(Protocol):
    """Base protocol for microscope actions"""
    
    @abstractmethod
    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute the action"""
        pass
    
    @abstractmethod
    def validate(self, state: MicroscopeState) -> bool:
        """Check if action is valid in current state"""
        pass
    
    @abstractmethod
    def predict_state(self, current_state: MicroscopeState) -> MicroscopeState:
        """Predict resulting state after action"""
        pass

class MoveStageTo(MicroscopeAction):
    """Move stage to specific position"""
    
    def __init__(self, target: StagePosition):
        self.target = target
    
    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute stage movement"""
        try:
            # Implementation would use hardware control
            return ActionResult(
                status=ActionStatus.COMPLETED,
                data={'position': self.target}
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.FAILED,
                data={},
                error=str(e)
            )
    
    def validate(self, state: MicroscopeState) -> bool:
        """Check if movement is within stage limits"""
        # Would check stage travel limits
        return True
    
    def predict_state(self, current_state: MicroscopeState) -> MicroscopeState:
        """Predict state after movement"""
        new_state = current_state.copy()
        new_state.stage = self.target
        new_state.last_action = "move_stage"
        return new_state

class AcquireImage(MicroscopeAction):
    """Acquire single image"""
    
    def __init__(self, exposure: float, channel: str):
        self.exposure = exposure
        self.channel = channel
    
    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute image acquisition"""
        try:
            # Implementation would use camera control
            return ActionResult(
                status=ActionStatus.COMPLETED,
                data={
                    'image': np.zeros((100, 100)),  # Placeholder
                    'exposure': self.exposure,
                    'channel': self.channel
                },
                energy_cost=self.exposure
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.FAILED,
                data={},
                error=str(e)
            )
    
    def validate(self, state: MicroscopeState) -> bool:
        """Check if acquisition is possible"""
        return (state.light_path.source == self.channel and
                0 < self.exposure <= 1000)  # ms
    
    def predict_state(self, current_state: MicroscopeState) -> MicroscopeState:
        """Predict state after acquisition"""
        new_state = current_state.copy()
        new_state.light_path.exposure = self.exposure
        new_state.last_action = "acquire_image"
        return new_state

class AutoFocus(MicroscopeAction):
    """Perform autofocus"""
    
    def __init__(self, range_um: float = 10.0, steps: int = 10):
        self.range = range_um
        self.steps = steps
    
    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute autofocus"""
        try:
            # Implementation would perform focus sweep
            return ActionResult(
                status=ActionStatus.COMPLETED,
                data={'focus_position': 0.0}  # Placeholder
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.FAILED,
                data={},
                error=str(e)
            )
    
    def validate(self, state: MicroscopeState) -> bool:
        """Check if autofocus is possible"""
        return True  # Would check hardware readiness
    
    def predict_state(self, current_state: MicroscopeState) -> MicroscopeState:
        """Predict state after autofocus"""
        new_state = current_state.copy()
        new_state.last_action = "autofocus"
        return new_state

@dataclass
class Perception:
    """Understanding built from observations"""
    entities: Dict[str, BiologicalEntity] = field(default_factory=dict)
    confidence: Dict[str, float] = field(default_factory=dict)
    spatial_context: Dict = field(default_factory=dict)
    temporal_context: Dict = field(default_factory=dict)
    quality_metrics: Dict = field(default_factory=dict)
    
    def update(self, observation: EntityObservation) -> None:
        """Update understanding based on new observation"""
        entity_id = observation.entity_id
        
        # Update or create entity
        if entity_id in self.entities:
            self.entities[entity_id].add_observation(observation)
        else:
            # Create new entity
            pass  # Implementation in biology.py
        
        # Update confidence
        self.confidence[entity_id] = observation.quality_metrics.get(
            'detection_confidence', 0.5)
        
        # Update contexts
        if observation.position:
            self.spatial_context[entity_id] = observation.position
        self.temporal_context[entity_id] = observation.timestamp
        
        # Update quality metrics
        self.quality_metrics.update(observation.quality_metrics)

class ObservationStrategy(Protocol):
    """Strategy for observing biological phenomena"""
    
    @abstractmethod
    def next_action(self, perception: Perception) -> MicroscopeAction:
        """Decide next action based on current perception"""
        pass
    
    @abstractmethod
    def is_complete(self, perception: Perception) -> bool:
        """Check if observation objective is met"""
        pass

class FindCellsStrategy(ObservationStrategy):
    """Strategy for finding cells in sample"""
    
    def __init__(self, cell_type: EntityType, min_count: int = 10):
        self.cell_type = cell_type
        self.min_count = min_count
        self.search_positions = self._generate_search_grid()
    
    def next_action(self, perception: Perception) -> MicroscopeAction:
        """Decide next action based on current perception"""
        # If we haven't found enough cells
        if len(perception.entities) < self.min_count:
            if self.search_positions:
                # Move to next search position
                next_pos = self.search_positions.pop(0)
                return MoveStageTo(next_pos)
            else:
                # Expand search area
                self.search_positions = self._generate_search_grid(expanded=True)
                return self.next_action(perception)
        
        # If we have cells but low confidence
        low_confidence = [
            eid for eid, conf in perception.confidence.items()
            if conf < 0.8
        ]
        if low_confidence:
            # Revisit position with longest time since last observation
            entity_id = max(
                low_confidence,
                key=lambda x: perception.temporal_context[x]
            )
            pos = perception.spatial_context[entity_id]
            return MoveStageTo(StagePosition(**pos))
        
        return None  # No action needed
    
    def is_complete(self, perception: Perception) -> bool:
        """Check if we've found enough cells confidently"""
        confident_cells = sum(
            1 for eid, conf in perception.confidence.items()
            if conf >= 0.8
        )
        return confident_cells >= self.min_count
    
    def _generate_search_grid(self, expanded: bool = False) -> List[StagePosition]:
        """Generate grid of positions to search"""
        # Implementation would generate spiral or grid pattern
        return []

class MicroscopyLoop:
    """Main action-perception loop"""
    
    def __init__(self, 
                 strategy: ObservationStrategy,
                 initial_state: MicroscopeState):
        self.strategy = strategy
        self.state = initial_state
        self.perception = Perception()
    
    async def run(self) -> Perception:
        """Run the action-perception loop"""
        while True:
            # 1. Decide next action
            action = self.strategy.next_action(self.perception)
            if action is None:
                break
            
            # 2. Validate action
            if not self.state.can_execute(action):
                raise ValueError(f"Invalid action: {action}")
            
            # 3. Execute action
            context = ActionContext(
                microscope_state=self.state,
                technical_params=TechnicalParameters(
                    pixel_size=0.1,
                    time_resolution=0.1,
                    channels={},
                    exposure_times={},
                    laser_powers={},
                    gain={}
                )
            )
            result = await action.execute(context)
            
            # 4. Handle failure
            if result.status == ActionStatus.FAILED:
                raise RuntimeError(f"Action failed: {result.error}")
            
            # 5. Update state
            self.state = action.predict_state(self.state)
            
            # 6. Update perception
            if 'observation' in result.data:
                self.perception.update(result.data['observation'])
            
            # 7. Check completion
            if self.strategy.is_complete(self.perception):
                break
        
        return self.perception
