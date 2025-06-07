"""Hardware abstraction layer for microscopy control."""

from .microscope import (
    Microscope,
    MicroscopyOperations,
    AdaptiveMicroscopyOperations
)

from .devices import (
    MMCoreInterface,
    Camera,
    Focus,
    Channel,
    AutoFocus,
    XYStage
)

from .channels import (
    ChannelConfig
)

__all__ = [
    # Microscope
    'Microscope',
    'MicroscopyOperations',
    'AdaptiveMicroscopyOperations',
    
    # Devices
    'MMCoreInterface',
    'Camera',
    'Focus', 
    'Channel',
    'AutoFocus',
    'XYStage',
    
    # Channels
    'ChannelConfig'
]