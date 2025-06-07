"""
Core biological concepts and models.

This module defines the fundamental biological entities and their properties,
separate from technical implementation details of observation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

class EntityType(Enum):
    """Types of biological entities we can observe"""
    CELL = auto()
    NUCLEUS = auto()
    MEMBRANE = auto()
    ORGANELLE = auto()
    PROTEIN_CLUSTER = auto()

@dataclass
class Morphology:
    """Natural morphological properties of an entity"""
    size: Tuple[float, float, float]  # x, y, z in microns
    shape_features: Dict[str, float]  # circularity, elongation, etc.
    boundary: np.ndarray  # Normalized boundary coordinates
    volume: float  # in cubic microns
    
    @property
    def area(self) -> float:
        """Get projected area in square microns"""
        return self.size[0] * self.size[1]

@dataclass
class Dynamics:
    """Dynamic behavior properties of an entity"""
    velocity: Optional[Tuple[float, float, float]] = None  # microns/second
    division_state: Optional[str] = None  # interphase, mitotic, etc.
    motion_type: Optional[str] = None  # directed, brownian, etc.
    last_division: Optional[datetime] = None
    
    def update_motion(self, new_position: Tuple[float, float, float],
                     timestamp: datetime) -> None:
        """Update motion state with new position observation"""
        # Implementation for motion analysis
        pass

@dataclass
class Composition:
    """Internal composition and structure of entity"""
    density: Dict[str, float]  # Density measures for different channels
    internal_structures: List['BiologicalEntity'] = field(default_factory=list)
    membrane_properties: Dict[str, float] = field(default_factory=dict)
    
    def add_internal_structure(self, entity: 'BiologicalEntity') -> None:
        """Add an internal structure to this entity"""
        self.internal_structures.append(entity)

@dataclass
class CellularState:
    """Current state of the biological entity"""
    cell_cycle_phase: Optional[str] = None
    viability: float = 1.0  # 0 to 1
    stress_level: float = 0.0  # 0 to 1
    age: Optional[float] = None  # hours
    
    def update_viability(self, new_observation: float) -> None:
        """Update viability based on new observation"""
        self.viability = 0.8 * self.viability + 0.2 * new_observation  # Smoothed update

@dataclass
class FluorescenceState:
    """Fluorescence properties including bleaching"""
    initial_intensities: Dict[str, float]  # Per channel
    current_intensities: Dict[str, float]  # Per channel
    bleaching_rates: Dict[str, float]  # Per channel
    recovery_rates: Dict[str, float]  # Per channel
    total_exposure: Dict[str, float]  # Cumulative exposure per channel
    
    def update_bleaching(self, channel: str, exposure_time: float) -> None:
        """Update bleaching state after exposure"""
        if channel not in self.current_intensities:
            return
            
        intensity = self.current_intensities[channel]
        bleach_rate = self.bleaching_rates[channel]
        recovery_rate = self.recovery_rates[channel]
        
        # Simple bleaching model with recovery
        decay = np.exp(-bleach_rate * exposure_time)
        recovery = (1 - decay) * recovery_rate
        
        new_intensity = intensity * decay + recovery
        self.current_intensities[channel] = new_intensity
        self.total_exposure[channel] += exposure_time

@dataclass
class LabelingState:
    """State of fluorescent labels and markers"""
    labels: Dict[str, str]  # Channel to label mapping
    labeling_efficiency: Dict[str, float]  # Efficiency per label
    label_density: Dict[str, float]  # Density of labeling
    background: Dict[str, float]  # Background per channel

@dataclass
class TreatmentResponse:
    """Entity's response to experimental treatments"""
    treatments: Dict[str, datetime]  # Treatment and time applied
    responses: Dict[str, float]  # Measured responses
    control_state: bool = True  # Whether entity is in control state
    
    def add_treatment(self, treatment: str, time: datetime) -> None:
        """Record application of treatment"""
        self.treatments[treatment] = time
        self.control_state = False

@dataclass
class EntityRelationships:
    """Relationships with other biological entities"""
    container: Optional['BiologicalEntity'] = None
    contained_entities: Set['BiologicalEntity'] = field(default_factory=set)
    neighbors: Dict['BiologicalEntity', float] = field(default_factory=dict)  # Entity to distance
    interactions: List[Tuple['BiologicalEntity', str, datetime]] = field(default_factory=list)
    
    def add_neighbor(self, entity: 'BiologicalEntity', distance: float) -> None:
        """Add or update a neighboring entity"""
        self.neighbors[entity] = distance
    
    def record_interaction(self, entity: 'BiologicalEntity', 
                         interaction_type: str, time: datetime) -> None:
        """Record an interaction with another entity"""
        self.interactions.append((entity, interaction_type, time))

@dataclass
class BiologicalProperties:
    """Properties inherent to the biological entity"""
    morphology: Morphology
    dynamics: Dynamics
    composition: Composition
    state: CellularState

@dataclass
class ExperimentalProperties:
    """Properties arising from experimental intervention"""
    fluorescence: FluorescenceState
    labeling: LabelingState
    treatment_response: TreatmentResponse

class BiologicalEntity:
    """A biological entity with its natural and experimental states"""
    
    def __init__(self, 
                 entity_id: str,
                 entity_type: EntityType,
                 creation_time: datetime,
                 natural_properties: BiologicalProperties,
                 experimental_properties: ExperimentalProperties):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.creation_time = creation_time
        self.natural_properties = natural_properties
        self.experimental_properties = experimental_properties
        self.relationships = EntityRelationships()
        self.observation_history: List['EntityObservation'] = []
        
    def add_observation(self, observation: 'EntityObservation') -> None:
        """Add new observation of this entity"""
        self.observation_history.append(observation)
        self._update_state_from_observation(observation)
    
    def _update_state_from_observation(self, observation: 'EntityObservation') -> None:
        """Update entity state based on new observation"""
        # Update natural properties
        if observation.morphology is not None:
            self.natural_properties.morphology = observation.morphology
        
        # Update dynamics
        if observation.position is not None:
            self.natural_properties.dynamics.update_motion(
                observation.position, observation.timestamp)
        
        # Update experimental properties
        for channel, exposure in observation.exposures.items():
            self.experimental_properties.fluorescence.update_bleaching(
                channel, exposure)
    
    def predict_state(self, target_time: datetime) -> 'BiologicalEntity':
        """Predict entity state at future time"""
        # Implementation for state prediction
        pass
    
    @property
    def age(self) -> float:
        """Get entity age in hours"""
        if not self.observation_history:
            return 0.0
        latest = self.observation_history[-1].timestamp
        return (latest - self.creation_time).total_seconds() / 3600

@dataclass
class EntityObservation:
    """A single observation of an entity"""
    entity_id: str
    timestamp: datetime
    position: Optional[Tuple[float, float, float]]
    morphology: Optional[Morphology]
    intensities: Dict[str, float]
    exposures: Dict[str, float]
    quality_metrics: Dict[str, float]
    metadata: Dict[str, any]

class BiologicalSample:
    """A biological sample containing multiple entities"""
    
    def __init__(self, sample_id: str):
        self.sample_id = sample_id
        self.entities: Dict[str, BiologicalEntity] = {}
        self.conditions = {}
        self.creation_time = datetime.now()
    
    def add_entity(self, entity: BiologicalEntity) -> None:
        """Add entity to sample"""
        self.entities[entity.entity_id] = entity
    
    def get_entities(self, entity_type: Optional[EntityType] = None) -> List[BiologicalEntity]:
        """Get entities, optionally filtered by type"""
        if entity_type is None:
            return list(self.entities.values())
        return [e for e in self.entities.values() if e.entity_type == entity_type]
    
    def update_condition(self, condition: str, value: any) -> None:
        """Update sample condition"""
        self.conditions[condition] = value
