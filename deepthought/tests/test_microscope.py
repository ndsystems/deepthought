"""Test suite for microscope functionality."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from ..hardware.microscope import Microscope
from ..exceptions import MicroscopyError

@pytest.fixture
def mock_mmc():
    """Create mock MMCore interface."""
    mock = MagicMock()
    mock.getProperty.return_value = "1"
    mock.snapImage.return_value = None
    mock.getImage.return_value = np.zeros((100, 100))
    return mock

@pytest.fixture
def microscope(mock_mmc):
    """Create test microscope instance."""
    return Microscope(mock_mmc)

def test_microscope_initialization(microscope):
    """Test microscope initialization."""
    assert microscope is not None
    assert microscope.hardware is not None

def test_snap_image(microscope):
    """Test image acquisition."""
    image = microscope.hardware.acquire_frame((0, 0), "DAPI")
    assert isinstance(image, np.ndarray)
    assert image.shape == (100, 100)

def test_invalid_channel(microscope):
    """Test error handling for invalid channel."""
    with pytest.raises(ConfigurationError):
        microscope.hardware.acquire_frame((0, 0), "INVALID")

@pytest.mark.asyncio
async def test_scan_xy(microscope):
    """Test XY scanning functionality."""
    channels = ["DAPI", "FITC"]
    async for frame in microscope.scan_xy(channels, num=2):
        assert frame is not None
        assert isinstance(frame.image, np.ndarray) 