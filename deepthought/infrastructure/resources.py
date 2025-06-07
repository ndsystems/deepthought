"""Resource management for microscope system."""

import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager
import gc
from pathlib import Path
import numpy as np
from exceptions import ResourceError

class ResourceManager:
    """Manages system resources and cleanup."""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.max_memory = config["max_memory_usage"]
        self.active_resources: Dict[str, Any] = {}
        self.temp_dir = Path(config["data_dir"]) / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    def register_resource(self, name: str, resource: Any) -> None:
        """Register a resource for tracking."""
        self.active_resources[name] = resource
        self.logger.debug(f"Registered resource: {name}")
        
    def release_resource(self, name: str) -> None:
        """Release a specific resource."""
        if name not in self.active_resources:
            return
            
        resource = self.active_resources[name]
        try:
            # Handle different resource types
            if hasattr(resource, 'close'):
                resource.close()
            elif hasattr(resource, 'cleanup'):
                resource.cleanup()
                
            del self.active_resources[name]
            self.logger.debug(f"Released resource: {name}")
            
        except Exception as e:
            self.logger.error(f"Error releasing resource {name}: {str(e)}")
            raise ResourceError(f"Failed to release resource {name}")
            
    def cleanup_all(self) -> None:
        """Release all registered resources."""
        for name in list(self.active_resources.keys()):
            self.release_resource(name)
            
        # Clear temporary files
        for file in self.temp_dir.glob("*"):
            try:
                file.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to delete temporary file {file}: {str(e)}")
                
        # Force garbage collection
        gc.collect()
        
    @contextmanager
    def temporary_array(self, shape: tuple, dtype=np.float32) -> np.ndarray:
        """Context manager for temporary array allocation."""
        array_size = np.prod(shape) * np.dtype(dtype).itemsize / (1024 * 1024)  # MB
        
        if array_size > self.max_memory:
            raise ResourceError(f"Array size ({array_size}MB) exceeds maximum allowed memory")
            
        try:
            array = np.empty(shape, dtype=dtype)
            yield array
        finally:
            del array
            gc.collect()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all() 