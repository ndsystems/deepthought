"""Custom exceptions for microscope automation system."""

class MicroscopeError(Exception):
    """Base exception for microscope-related errors."""
    pass

class HardwareError(MicroscopeError):
    """Errors related to hardware operations."""
    pass

class ConfigurationError(MicroscopeError):
    """Errors related to system configuration."""
    pass

class ProcessingError(MicroscopeError):
    """Errors related to image processing."""
    pass

class ResourceError(MicroscopeError):
    """Errors related to resource management."""
    pass 