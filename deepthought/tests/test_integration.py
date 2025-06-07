"""Integration tests for microscope system."""

import pytest
import numpy as np
from pathlib import Path
from ..hardware.microscope import Microscope
from ..infrastructure.resources import ResourceManager
from ..exceptions import MicroscopyError

@pytest.fixture
def system_setup():
    """Set up complete system for integration testing."""
    config_path = Path(__file__).parent / "test_config.yaml"
    config_manager = ConfigManager(str(config_path))
    resource_manager = ResourceManager(config_manager.config["system"])
    
    return config_manager, resource_manager

@pytest.mark.integration
class TestMicroscopeIntegration:
    """Integration tests for microscope operations."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, system_setup):
        """Test complete microscope workflow."""
        config_manager, resource_manager = system_setup
        
        with resource_manager:
            microscope = Microscope(
                config_manager.get_microscope_config("test_scope"),
                resource_manager
            )
            
            # Test initialization
            assert microscope.is_initialized()
            
            # Test channel switching
            await microscope.set_channel("DAPI")
            current_channel = await microscope.get_current_channel()
            assert current_channel == "DAPI"
            
            # Test image acquisition
            image = await microscope.acquire_image()
            assert isinstance(image, np.ndarray)
            assert not np.all(image == 0)  # Check if image contains data
            
            # Test scanning
            scan_results = []
            async for frame in microscope.scan_xy(["DAPI", "FITC"], num=2):
                scan_results.append(frame)
                
            assert len(scan_results) > 0
            
    @pytest.mark.asyncio
    async def test_error_recovery(self, system_setup):
        """Test system recovery from errors."""
        config_manager, resource_manager = system_setup
        
        with resource_manager:
            microscope = Microscope(
                config_manager.get_microscope_config("test_scope"),
                resource_manager
            )
            
            # Test recovery from channel error
            with pytest.raises(MicroscopeError):
                await microscope.set_channel("INVALID_CHANNEL")
                
            # System should still be functional
            await microscope.set_channel("DAPI")
            assert await microscope.get_current_channel() == "DAPI" 