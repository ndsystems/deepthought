"""DeepThought: Intelligent Microscopy Control System.

A modern action-perception loop architecture for automated microscopy.
"""

from .version import __version__, __version_info__, get_version

# Core action-perception architecture
from .core import (
    MicroscopyLoop,
    MicroscopeAction,
    MicroscopeState,
    Perception,
    ObservationStrategy,
    CellTrackingExperiment,
    TissueMappingExperiment,
    CompositeStrategy,
    MapSampleStrategy
)

# Domain models
from .domain import (
    BiologicalEntity,
    BiologicalSample,
    EntityType,
    ObservationSet,
    TechnicalParameters
)

# Hardware control
from .hardware import (
    Microscope,
    MMCoreInterface,
    ChannelConfig
)

# Analysis
from .analysis import (
    NuclearDetector
)

# Entry point
from .cli import main

__all__ = [
    # Version info
    '__version__', 
    '__version_info__', 
    'get_version',
    
    # Core architecture
    'MicroscopyLoop',
    'MicroscopeAction', 
    'MicroscopeState',
    'Perception',
    'ObservationStrategy',
    'CellTrackingExperiment',
    'TissueMappingExperiment',
    'CompositeStrategy',
    'MapSampleStrategy',
    
    # Domain models
    'BiologicalEntity',
    'BiologicalSample',
    'EntityType', 
    'ObservationSet',
    'TechnicalParameters',
    
    # Hardware
    'Microscope',
    'MMCoreInterface',
    'ChannelConfig',
    
    # Analysis
    'NuclearDetector',
    
    # CLI
    'main'
]
