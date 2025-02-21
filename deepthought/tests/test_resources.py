"""Test suite for resource management."""

import pytest
import numpy as np
from pathlib import Path
from resources import ResourceManager
from exceptions import ResourceError

@pytest.fixture
def config():
    """Create test configuration."""
    return {
        "max_memory_usage": 1024,  # 1GB
        "data_dir": "test_data"
    }

@pytest.fixture
def resource_manager(config):
    """Create test resource manager."""
    return ResourceManager(config)

class MockResource:
    """Mock resource for testing."""
    def __init__(self):
        self.cleaned_up = False
        
    def cleanup(self):
        self.cleaned_up = True

def test_resource_registration(resource_manager):
    """Test resource registration and release."""
    resource = MockResource()
    
    # Test registration
    resource_manager.register_resource("test", resource)
    assert "test" in resource_manager.active_resources
    
    # Test release
    resource_manager.release_resource("test")
    assert "test" not in resource_manager.active_resources
    assert resource.cleaned_up

def test_temporary_array(resource_manager):
    """Test temporary array allocation."""
    shape = (1000, 1000)  # ~4MB for float32
    
    with resource_manager.temporary_array(shape) as array:
        assert isinstance(array, np.ndarray)
        assert array.shape == shape
        
    # Test memory error
    huge_shape = (50000, 50000)  # ~10GB
    with pytest.raises(ResourceError):
        with resource_manager.temporary_array(huge_shape):
            pass

def test_cleanup_all(resource_manager):
    """Test cleanup of all resources."""
    resources = [MockResource() for _ in range(3)]
    
    for i, resource in enumerate(resources):
        resource_manager.register_resource(f"test_{i}", resource)
        
    resource_manager.cleanup_all()
    
    assert len(resource_manager.active_resources) == 0
    assert all(r.cleaned_up for r in resources)

def test_context_manager(config):
    """Test resource manager as context manager."""
    with ResourceManager(config) as rm:
        resource = MockResource()
        rm.register_resource("test", resource)
        
    assert resource.cleaned_up 