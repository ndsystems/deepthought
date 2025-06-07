"""Test suite for hardware integration with Bluesky patterns."""

import pytest
import asyncio
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from bluesky import plan_stubs

from ..hardware.microscope import (
    Microscope,
    MicroscopyOperations, 
    AdaptiveMicroscopyOperations,
    MicroscopyError,
    HardwareError,
    FocusError,
    AcquisitionError
)
from ..hardware.devices import MMCoreInterface, Camera, Focus, XYStage
from ..hardware.channels import ChannelConfig
from ..domain.biology import BiologicalSample, BiologicalEntity, EntityType
from ..domain.observation import TechnicalParameters


@pytest.fixture
def mock_mmc():
    """Create mock MMCore interface."""
    mock = MagicMock()
    mock.getProperty.return_value = "1"
    mock.snapImage.return_value = None
    mock.getImage.return_value = np.random.randint(0, 4096, (100, 100))
    mock.setProperty.return_value = None
    return mock


@pytest.fixture
def mock_hardware(mock_mmc):
    """Create mock hardware with MMCore."""
    hardware = MagicMock()
    hardware._mmc = mock_mmc
    hardware.cam = MagicMock()
    hardware.z = MagicMock()
    hardware.stage = MagicMock()
    hardware.ch = MagicMock()
    
    # Setup async methods
    hardware.snap_image_and_other_readings_too = AsyncMock()
    hardware.auto_exposure = AsyncMock()
    hardware.get_pixel_size = MagicMock(return_value=0.1)
    hardware.get_magnification = MagicMock(return_value=60)
    hardware.get_binning = MagicMock(return_value=1)
    hardware.generate_grid = MagicMock(return_value=MagicMock())
    
    return hardware


@pytest.fixture
def microscopy_operations(mock_hardware):
    """Create microscopy operations with mock hardware."""
    return MicroscopyOperations(mock_hardware)


@pytest.fixture
def biological_sample():
    """Create test biological sample."""
    sample = BiologicalSample("test_sample")
    return sample


@pytest.fixture
def technical_parameters():
    """Create test technical parameters."""
    return TechnicalParameters(
        pixel_size=0.1,
        time_resolution=1.0,
        channels={"DAPI": {"exposure": 50, "laser_power": 10}},
        exposure_times={"DAPI": 50},
        laser_powers={"488nm": 10},
        gain={"camera": 1.0}
    )


class TestMicroscopyError:
    """Test microscopy error hierarchy."""
    
    def test_base_error(self):
        """Test base microscopy error."""
        error = MicroscopyError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_hardware_error(self):
        """Test hardware error inheritance."""
        error = HardwareError("Hardware failure")
        assert isinstance(error, MicroscopyError)
        assert str(error) == "Hardware failure"
    
    def test_focus_error(self):
        """Test focus error inheritance."""
        error = FocusError("Focus failure")
        assert isinstance(error, MicroscopyError)
        assert str(error) == "Focus failure"
    
    def test_acquisition_error(self):
        """Test acquisition error inheritance."""
        error = AcquisitionError("Acquisition failure")
        assert isinstance(error, MicroscopyError)
        assert str(error) == "Acquisition failure"


class TestMicroscopyOperations:
    """Test microscopy operations using Bluesky patterns."""
    
    @pytest.mark.asyncio
    async def test_create_microscope_state(self, microscopy_operations):
        """Test microscope state creation."""
        with patch('bluesky.plan_stubs.rd') as mock_rd:
            # Mock hardware readings
            mock_rd.return_value = AsyncMock()
            
            state = await microscopy_operations._create_microscope_state()
            
            assert state.pixel_size == 0.1
            assert state.magnification == 60
            assert state.binning == 1
    
    @pytest.mark.asyncio
    async def test_find_sample_plane(self, microscopy_operations):
        """Test sample plane finding with focus."""
        with patch.object(microscopy_operations, '_coarse_focus_sweep', new_callable=AsyncMock) as mock_coarse, \
             patch.object(microscopy_operations, '_fine_focus_sweep', new_callable=AsyncMock) as mock_fine, \
             patch('bluesky.plan_stubs.mv', new_callable=AsyncMock) as mock_mv:
            
            await microscopy_operations.find_sample_plane()
            
            mock_coarse.assert_called_once()
            mock_fine.assert_called_once()
            mock_mv.assert_called()
    
    @pytest.mark.asyncio
    async def test_focus_sweep(self, microscopy_operations):
        """Test focus sweep operation."""
        with patch('bluesky.plan_stubs.rd', new_callable=AsyncMock) as mock_rd, \
             patch('bluesky.plan_stubs.mv', new_callable=AsyncMock) as mock_mv, \
             patch.object(microscopy_operations, '_calculate_focus_score', new_callable=AsyncMock) as mock_focus_score:
            
            mock_rd.return_value = 100.0  # Current Z position
            mock_focus_score.side_effect = [0.5, 0.8, 0.6, 0.4]  # Focus scores
            
            best_z = await microscopy_operations._coarse_focus_sweep(range_um=20, steps=4)
            
            # Should have moved to position with highest focus score (0.8)
            assert mock_mv.call_count >= 4  # 4 test positions + final move
            assert isinstance(best_z, float)
    
    @pytest.mark.asyncio
    async def test_acquire_frame_with_metadata(self, microscopy_operations):
        """Test frame acquisition with full metadata."""
        from ..hardware.microscope import Position, Channel
        
        position = Position(x=100, y=200, z=50)
        channel = Channel(name="DAPI", exposure=50)
        
        with patch('bluesky.plan_stubs.rd', new_callable=AsyncMock) as mock_rd:
            mock_rd.return_value = np.random.randint(0, 4096, (100, 100))
            
            frame = await microscopy_operations._acquire_frame_with_metadata(position, channel)
            
            assert frame.position == position
            assert frame.channel == channel
            assert isinstance(frame.image, np.ndarray)
            assert frame.microscope_settings is not None
    
    @pytest.mark.asyncio
    async def test_find_region_of_interest(self, microscopy_operations):
        """Test region of interest finding."""
        with patch('bluesky.plan_stubs.rd', new_callable=AsyncMock) as mock_rd, \
             patch('bluesky.plan_stubs.mv', new_callable=AsyncMock) as mock_mv, \
             patch.object(microscopy_operations, '_analyze_position', new_callable=AsyncMock) as mock_analyze:
            
            # Mock current position
            mock_rd.return_value = (500, 600)
            
            # Mock grid generation
            mock_grid = MagicMock()
            mock_grid.midpoints.return_value = [
                {"x": 490, "y": 590},
                {"x": 500, "y": 600},
                {"x": 510, "y": 610}
            ]
            microscopy_operations.hw.generate_grid.return_value = mock_grid
            
            # Mock analysis results (count, position)
            mock_analyze.side_effect = [
                (3, MagicMock(x=490, y=590)),
                (8, MagicMock(x=500, y=600)),  # Best position
                (2, MagicMock(x=510, y=610))
            ]
            
            result = await microscopy_operations.find_region_of_interest(threshold=5)
            
            assert result is True
            mock_mv.assert_called()  # Should move to best position
    
    @pytest.mark.asyncio
    async def test_tile_region(self, microscopy_operations):
        """Test tiled acquisition planning."""
        center = (1000, 1000)
        size = (500, 500)
        overlap = 0.1
        
        # Mock field of view
        microscopy_operations.hw.estimate_axial_length.return_value = 100
        
        positions = await microscopy_operations.tile_region(center, size, overlap)
        
        assert len(positions) > 0
        assert all(isinstance(pos, tuple) and len(pos) == 2 for pos in positions)
        
        # Check that positions cover the region
        x_coords, y_coords = zip(*positions)
        assert min(x_coords) >= center[0] - size[0]/2
        assert max(x_coords) <= center[0] + size[0]/2
    
    @pytest.mark.asyncio
    async def test_error_handling(self, microscopy_operations):
        """Test error handling in operations."""
        with patch('bluesky.plan_stubs.mv', new_callable=AsyncMock) as mock_mv:
            mock_mv.side_effect = Exception("Hardware failure")
            
            with pytest.raises(HardwareError):
                await microscopy_operations.find_sample_plane()


class TestAdaptiveMicroscopyOperations:
    """Test adaptive microscopy operations."""
    
    @pytest.fixture
    def adaptive_operations(self, mock_hardware):
        """Create adaptive operations with mock hardware."""
        return AdaptiveMicroscopyOperations(mock_hardware)
    
    @pytest.mark.asyncio
    async def test_load_sample(self, adaptive_operations, biological_sample):
        """Test sample loading."""
        await adaptive_operations.load_sample(biological_sample)
        
        assert adaptive_operations.current_sample == biological_sample
    
    @pytest.mark.asyncio
    async def test_configure_observation(self, adaptive_operations, technical_parameters):
        """Test observation configuration."""
        await adaptive_operations.configure_observation(technical_parameters)
        
        # Verify method was configured
        assert adaptive_operations.observation_method.parameters == technical_parameters
    
    @pytest.mark.asyncio
    async def test_observe_entities_no_sample(self, adaptive_operations):
        """Test observation without loaded sample."""
        with pytest.raises(ValueError, match="No sample loaded"):
            await adaptive_operations.observe_entities()
    
    @pytest.mark.asyncio
    async def test_find_entity(self, adaptive_operations, biological_sample):
        """Test entity finding in sample."""
        # Create mock entity
        from ..domain.biology import BiologicalProperties, ExperimentalProperties
        entity = MagicMock()
        entity.entity_type = EntityType.CELL
        entity.observation_history = []
        
        await adaptive_operations.load_sample(biological_sample)
        
        with patch('bluesky.plan_stubs.rd', new_callable=AsyncMock) as mock_rd, \
             patch('bluesky.plan_stubs.mv', new_callable=AsyncMock) as mock_mv, \
             patch.object(adaptive_operations, '_observe_position', new_callable=AsyncMock) as mock_observe:
            
            mock_rd.return_value = (500, 600)
            
            # Mock grid and observations
            mock_grid = MagicMock()
            mock_grid.midpoints.return_value = [{"x": 500, "y": 600}]
            adaptive_operations.hw.generate_grid.return_value = mock_grid
            
            # Mock finding entities
            mock_entity_result = MagicMock()
            mock_entity_result.characteristics.entity_type = EntityType.CELL
            mock_entity_result.confidence.detection_confidence = 0.8
            mock_observe.return_value = [mock_entity_result] * 6  # Above threshold
            
            position = await adaptive_operations._find_entity(entity)
            
            assert position is not None
            mock_mv.assert_called()  # Should move to best position


class TestChannelConfig:
    """Test channel configuration."""
    
    def test_creation(self):
        """Test channel config creation."""
        config = ChannelConfig("DAPI")
        
        assert config.name == "DAPI"
        assert hasattr(config, 'exposure')
        assert hasattr(config, 'detector')
        assert hasattr(config, 'marker')
    
    def test_configuration(self):
        """Test channel configuration."""
        config = ChannelConfig("FITC")
        config.exposure = 100
        config.marker = "GFP"
        
        assert config.exposure == 100
        assert config.marker == "GFP"


class TestMMCoreInterface:
    """Test MMCore interface wrapper."""
    
    def test_creation(self):
        """Test MMCore interface creation."""
        interface = MMCoreInterface()
        
        assert hasattr(interface, 'scopes')
    
    def test_add_scope(self):
        """Test adding microscope to interface."""
        interface = MMCoreInterface()
        interface.add("127.0.0.1", "test_scope")
        
        assert "test_scope" in interface.scopes


class TestMicroscope:
    """Test main microscope interface."""
    
    def test_creation(self, mock_mmc):
        """Test microscope creation."""
        microscope = Microscope(mock_mmc)
        
        assert microscope.hardware is not None
        assert microscope.operations is not None
        assert microscope.adaptive_operations is not None
    
    @pytest.mark.asyncio
    async def test_find_sample(self, mock_mmc):
        """Test sample finding convenience method."""
        microscope = Microscope(mock_mmc)
        
        with patch.object(microscope.operations, 'find_sample_plane', new_callable=AsyncMock) as mock_find_plane, \
             patch.object(microscope.operations, 'find_region_of_interest', new_callable=AsyncMock) as mock_find_roi:
            
            await microscope.find_sample()
            
            mock_find_plane.assert_called_once()
            mock_find_roi.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_channel_acquisition(self, mock_mmc):
        """Test multi-channel acquisition."""
        microscope = Microscope(mock_mmc)
        channels = ["DAPI", "FITC", "TxRed"]
        
        with patch('bluesky.plan_stubs.mv', new_callable=AsyncMock) as mock_mv, \
             patch('bluesky.plan_stubs.rd', new_callable=AsyncMock) as mock_rd:
            
            mock_rd.return_value = np.random.randint(0, 4096, (100, 100))
            
            results = await microscope.multi_channel_acquisition(channels, auto_expose=False)
            
            assert len(results) == len(channels)
            for channel in channels:
                assert channel in results
                assert isinstance(results[channel], np.ndarray)