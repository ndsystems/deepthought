"""Shared test configuration and fixtures."""

import pytest
import numpy as np
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from ..core.loop import StagePosition, Objective, LightPath, MicroscopeState
from ..domain.biology import (
    BiologicalEntity, 
    BiologicalSample, 
    EntityType,
    BiologicalProperties,
    ExperimentalProperties,
    Morphology,
    Dynamics,
    Composition,
    CellularState,
    FluorescenceState,
    LabelingState,
    TreatmentResponse
)
from ..domain.observation import TechnicalParameters


@pytest.fixture
def mock_mmc():
    """Global mock MMCore interface."""
    mock = MagicMock()
    mock.getProperty.return_value = "1"
    mock.snapImage.return_value = None
    mock.getImage.return_value = np.random.randint(0, 4096, (100, 100))
    mock.setProperty.return_value = None
    return mock


@pytest.fixture
def standard_stage_position():
    """Standard test stage position."""
    return StagePosition(x=100.0, y=200.0, z=50.0)


@pytest.fixture
def standard_objective():
    """Standard test objective."""
    return Objective(
        magnification=60.0,
        numerical_aperture=1.4,
        working_distance=0.17,
        is_air=False
    )


@pytest.fixture
def standard_light_path():
    """Standard test light path."""
    return LightPath(
        source="DAPI",
        intensity=50.0,
        exposure=100.0,
        filters=["DAPI_filter"]
    )


@pytest.fixture
def standard_microscope_state(standard_stage_position, standard_objective, standard_light_path):
    """Standard test microscope state."""
    return MicroscopeState(
        objective=standard_objective,
        stage=standard_stage_position,
        light_path=standard_light_path,
        temperature=37.0,
        last_action=None
    )


@pytest.fixture
def standard_technical_params():
    """Standard test technical parameters."""
    return TechnicalParameters(
        pixel_size=0.1,
        time_resolution=1.0,
        channels={"DAPI": {"exposure": 50, "laser_power": 10}},
        exposure_times={"DAPI": 50},
        laser_powers={"488nm": 10},
        gain={"camera": 1.0}
    )


@pytest.fixture  
def standard_biological_entity():
    """Standard test biological entity."""
    # Create properties
    morphology = Morphology(
        size=(10.0, 15.0, 5.0),
        shape_features={"circularity": 0.8},
        boundary=np.array([[0, 0], [10, 0], [10, 10], [0, 10]]),
        volume=750.0
    )
    
    dynamics = Dynamics(
        velocity=(0.5, 0.3, 0.0),
        division_state="interphase",
        motion_type="directed"
    )
    
    composition = Composition(
        density={"DAPI": 1000},
        internal_structures=[],
        membrane_properties={}
    )
    
    cellular_state = CellularState(
        cell_cycle_phase="G1",
        viability=0.95,
        stress_level=0.1,
        age=24.0
    )
    
    fluorescence_state = FluorescenceState(
        initial_intensities={"DAPI": 1000},
        current_intensities={"DAPI": 950},
        bleaching_rates={"DAPI": 0.01},
        recovery_rates={"DAPI": 0.005},
        total_exposure={"DAPI": 100}
    )
    
    labeling_state = LabelingState(
        labels={"DAPI": "Hoechst"},
        labeling_efficiency={"DAPI": 0.95},
        label_density={"DAPI": 1000},
        background={"DAPI": 50}
    )
    
    treatment_response = TreatmentResponse(
        treatments={},
        responses={},
        control_state=True
    )
    
    biological_props = BiologicalProperties(
        morphology=morphology,
        dynamics=dynamics,
        composition=composition,
        state=cellular_state
    )
    
    experimental_props = ExperimentalProperties(
        fluorescence=fluorescence_state,
        labeling=labeling_state,
        treatment_response=treatment_response
    )
    
    return BiologicalEntity(
        entity_id="test_cell_001",
        entity_type=EntityType.CELL,
        creation_time=datetime.now() - timedelta(hours=24),
        natural_properties=biological_props,
        experimental_properties=experimental_props
    )


@pytest.fixture
def standard_biological_sample(standard_biological_entity):
    """Standard test biological sample."""
    sample = BiologicalSample("test_sample")
    sample.add_entity(standard_biological_entity)
    return sample


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "hardware: mark test as requiring hardware"
    )