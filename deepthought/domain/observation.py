"""
Observation framework for biological entities.

This module provides the interface between biological entities and technical
implementation details of microscopy.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Protocol, Tuple
import numpy as np

from .biology import (
    BiologicalEntity,
    BiologicalSample,
    EntityObservation,
    EntityType,
    Morphology
)

@dataclass
class TechnicalParameters:
    """Technical parameters for observation"""
    pixel_size: float  # microns
    time_resolution: float  # seconds
    channels: Dict[str, Dict]  # Channel configurations
    exposure_times: Dict[str, float]  # seconds
    laser_powers: Dict[str, float]  # percent
    gain: Dict[str, float]
    
    def get_channel_config(self, channel: str) -> Dict:
        """Get configuration for specific channel"""
        return self.channels.get(channel, {})

@dataclass
class QualityMetrics:
    """Quality metrics for an observation"""
    signal_to_noise: float
    focus_score: float
    motion_blur: float
    bleaching_estimate: float
    
    @property
    def is_usable(self) -> bool:
        """Whether observation meets quality thresholds"""
        return (self.signal_to_noise > 3.0 and
                self.focus_score > 0.5 and
                self.motion_blur < 0.3)

@dataclass
class TechnicalDetails:
    """Technical details of an observation"""
    raw_data: Dict[str, np.ndarray]  # Channel to image mapping
    parameters: TechnicalParameters
    quality: QualityMetrics
    metadata: Dict[str, any] = field(default_factory=dict)

class ObservationMethod(Protocol):
    """Protocol for methods that can observe biological entities"""
    
    def configure(self, parameters: TechnicalParameters) -> None:
        """Configure observation parameters"""
        ...
    
    def observe(self, sample: BiologicalSample) -> List[EntityObservation]:
        """Make observations of entities in sample"""
        ...

class EntityTracker:
    """Tracks entities across observations"""
    
    def __init__(self):
        self.tracked_entities: Dict[str, BiologicalEntity] = {}
        self._next_id = 0
    
    def add_observation(self, 
                       observation: EntityObservation,
                       technical_details: TechnicalDetails) -> None:
        """Add new observation, creating or updating entity"""
        entity_id = observation.entity_id
        
        if entity_id not in self.tracked_entities:
            # Create new entity
            entity = self._create_entity(observation, technical_details)
            self.tracked_entities[entity_id] = entity
        else:
            # Update existing entity
            self.tracked_entities[entity_id].add_observation(observation)
    
    def _create_entity(self,
                      observation: EntityObservation,
                      technical_details: TechnicalDetails) -> BiologicalEntity:
        """Create new entity from observation"""
        from .biology import (
            BiologicalProperties,
            Composition,
            CellularState,
            Dynamics,
            ExperimentalProperties,
            FluorescenceState,
            LabelingState,
            TreatmentResponse
        )
        
        # Create natural properties
        natural_props = BiologicalProperties(
            morphology=observation.morphology or self._default_morphology(),
            dynamics=Dynamics(),
            composition=Composition(density={}),
            state=CellularState()
        )
        
        # Create experimental properties
        experimental_props = ExperimentalProperties(
            fluorescence=FluorescenceState(
                initial_intensities=observation.intensities.copy(),
                current_intensities=observation.intensities.copy(),
                bleaching_rates={ch: 0.0 for ch in observation.intensities},
                recovery_rates={ch: 0.0 for ch in observation.intensities},
                total_exposure=observation.exposures.copy()
            ),
            labeling=LabelingState(
                labels={},
                labeling_efficiency={},
                label_density={},
                background={}
            ),
            treatment_response=TreatmentResponse(
                treatments={},
                responses={}
            )
        )
        
        return BiologicalEntity(
            entity_id=observation.entity_id,
            entity_type=self._infer_entity_type(observation),
            creation_time=observation.timestamp,
            natural_properties=natural_props,
            experimental_properties=experimental_props
        )
    
    def _default_morphology(self) -> Morphology:
        """Create default morphology"""
        return Morphology(
            size=(10.0, 10.0, 10.0),  # Default 10 micron size
            shape_features={},
            boundary=np.array([]),
            volume=1000.0  # 1000 cubic microns
        )
    
    def _infer_entity_type(self, observation: EntityObservation) -> EntityType:
        """Infer entity type from observation"""
        # Simple inference based on size and channels
        if 'DAPI' in observation.intensities:
            return EntityType.NUCLEUS
        if 'membrane' in observation.intensities:
            return EntityType.MEMBRANE
        return EntityType.CELL  # Default to cell

class ObservationSet:
    """A set of observations made at the same time"""
    
    def __init__(self, timestamp: datetime):
        self.timestamp = timestamp
        self.observations: List[EntityObservation] = []
        self.technical_details: Optional[TechnicalDetails] = None
    
    def add_observation(self, observation: EntityObservation) -> None:
        """Add observation to set"""
        self.observations.append(observation)
    
    def set_technical_details(self, details: TechnicalDetails) -> None:
        """Set technical details for this observation set"""
        self.technical_details = details

class MicroscopyMethod:
    """Base class for microscopy-based observation methods"""
    
    def __init__(self):
        self.parameters: Optional[TechnicalParameters] = None
    
    def configure(self, parameters: TechnicalParameters) -> None:
        """Configure microscopy parameters"""
        self.parameters = parameters
    
    def observe(self, sample: BiologicalSample) -> List[EntityObservation]:
        """Make observations using microscopy"""
        if self.parameters is None:
            raise ValueError("Method must be configured before use")
        
        # Implementation would use microscope to observe sample
        pass
    
    def _calculate_quality_metrics(self,
                                 images: Dict[str, np.ndarray]) -> QualityMetrics:
        """Calculate quality metrics for observation"""
        # Implementation for quality calculation
        pass
