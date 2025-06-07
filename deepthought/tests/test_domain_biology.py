"""Test suite for domain biology models."""

import pytest
import numpy as np
from datetime import datetime, timedelta

from ..domain.biology import (
    BiologicalEntity,
    BiologicalSample,
    EntityType,
    Morphology,
    Dynamics,
    Composition,
    CellularState,
    FluorescenceState,
    LabelingState,
    TreatmentResponse,
    EntityRelationships,
    BiologicalProperties,
    ExperimentalProperties,
    EntityObservation
)


@pytest.fixture
def morphology():
    """Create test morphology."""
    boundary = np.array([[0, 0], [10, 0], [10, 10], [0, 10]])
    return Morphology(
        size=(10.0, 15.0, 5.0),
        shape_features={"circularity": 0.8, "elongation": 1.5},
        boundary=boundary,
        volume=750.0
    )


@pytest.fixture
def dynamics():
    """Create test dynamics."""
    return Dynamics(
        velocity=(0.5, 0.3, 0.0),
        division_state="interphase",
        motion_type="directed",
        last_division=datetime.now() - timedelta(hours=12)
    )


@pytest.fixture
def composition():
    """Create test composition."""
    return Composition(
        density={"DAPI": 1000, "FITC": 500},
        internal_structures=[],
        membrane_properties={"permeability": 0.3}
    )


@pytest.fixture
def cellular_state():
    """Create test cellular state."""
    return CellularState(
        cell_cycle_phase="G1",
        viability=0.95,
        stress_level=0.1,
        age=24.0
    )


@pytest.fixture
def fluorescence_state():
    """Create test fluorescence state."""
    return FluorescenceState(
        initial_intensities={"DAPI": 1000, "FITC": 800},
        current_intensities={"DAPI": 950, "FITC": 750},
        bleaching_rates={"DAPI": 0.01, "FITC": 0.02},
        recovery_rates={"DAPI": 0.005, "FITC": 0.001},
        total_exposure={"DAPI": 100, "FITC": 150}
    )


@pytest.fixture
def labeling_state():
    """Create test labeling state."""
    return LabelingState(
        labels={"DAPI": "Hoechst", "FITC": "GFP"},
        labeling_efficiency={"DAPI": 0.95, "FITC": 0.8},
        label_density={"DAPI": 1000, "FITC": 500},
        background={"DAPI": 50, "FITC": 30}
    )


@pytest.fixture
def treatment_response():
    """Create test treatment response."""
    return TreatmentResponse(
        treatments={"drug_A": datetime.now() - timedelta(hours=2)},
        responses={"viability": 0.8, "proliferation": 0.6},
        control_state=False
    )


@pytest.fixture
def biological_properties(morphology, dynamics, composition, cellular_state):
    """Create test biological properties."""
    return BiologicalProperties(
        morphology=morphology,
        dynamics=dynamics,
        composition=composition,
        state=cellular_state
    )


@pytest.fixture
def experimental_properties(fluorescence_state, labeling_state, treatment_response):
    """Create test experimental properties."""
    return ExperimentalProperties(
        fluorescence=fluorescence_state,
        labeling=labeling_state,
        treatment_response=treatment_response
    )


@pytest.fixture
def biological_entity(biological_properties, experimental_properties):
    """Create test biological entity."""
    return BiologicalEntity(
        entity_id="cell_001",
        entity_type=EntityType.CELL,
        creation_time=datetime.now() - timedelta(hours=24),
        natural_properties=biological_properties,
        experimental_properties=experimental_properties
    )


class TestMorphology:
    """Test morphology functionality."""
    
    def test_creation(self, morphology):
        """Test morphology creation."""
        assert morphology.size == (10.0, 15.0, 5.0)
        assert morphology.volume == 750.0
        assert morphology.shape_features["circularity"] == 0.8
    
    def test_area_calculation(self, morphology):
        """Test area property calculation."""
        expected_area = 10.0 * 15.0
        assert morphology.area == expected_area


class TestDynamics:
    """Test dynamics functionality."""
    
    def test_creation(self, dynamics):
        """Test dynamics creation."""
        assert dynamics.velocity == (0.5, 0.3, 0.0)
        assert dynamics.division_state == "interphase"
        assert dynamics.motion_type == "directed"
    
    def test_update_motion(self, dynamics):
        """Test motion update."""
        new_position = (10.0, 15.0, 5.0)
        timestamp = datetime.now()
        
        # This would update velocity calculation
        dynamics.update_motion(new_position, timestamp)
        # Implementation would update velocity based on position change


class TestCellularState:
    """Test cellular state functionality."""
    
    def test_creation(self, cellular_state):
        """Test cellular state creation."""
        assert cellular_state.cell_cycle_phase == "G1"
        assert cellular_state.viability == 0.95
        assert cellular_state.stress_level == 0.1
        assert cellular_state.age == 24.0
    
    def test_viability_update(self, cellular_state):
        """Test viability update with smoothing."""
        initial_viability = cellular_state.viability
        cellular_state.update_viability(0.8)
        
        # Should be smoothed average
        expected = 0.8 * initial_viability + 0.2 * 0.8
        assert cellular_state.viability == expected


class TestFluorescenceState:
    """Test fluorescence state functionality."""
    
    def test_creation(self, fluorescence_state):
        """Test fluorescence state creation."""
        assert fluorescence_state.initial_intensities["DAPI"] == 1000
        assert fluorescence_state.current_intensities["FITC"] == 750
        assert fluorescence_state.total_exposure["DAPI"] == 100
    
    def test_bleaching_update(self, fluorescence_state):
        """Test bleaching calculation."""
        initial_intensity = fluorescence_state.current_intensities["DAPI"]
        initial_exposure = fluorescence_state.total_exposure["DAPI"]
        
        # Apply bleaching
        fluorescence_state.update_bleaching("DAPI", 50.0)
        
        # Intensity should decrease due to bleaching
        assert fluorescence_state.current_intensities["DAPI"] < initial_intensity
        
        # Total exposure should increase
        assert fluorescence_state.total_exposure["DAPI"] == initial_exposure + 50.0


class TestTreatmentResponse:
    """Test treatment response functionality."""
    
    def test_creation(self, treatment_response):
        """Test treatment response creation."""
        assert "drug_A" in treatment_response.treatments
        assert treatment_response.responses["viability"] == 0.8
        assert not treatment_response.control_state
    
    def test_add_treatment(self, treatment_response):
        """Test adding new treatment."""
        time = datetime.now()
        treatment_response.add_treatment("drug_B", time)
        
        assert "drug_B" in treatment_response.treatments
        assert treatment_response.treatments["drug_B"] == time
        assert not treatment_response.control_state


class TestEntityRelationships:
    """Test entity relationships functionality."""
    
    def test_creation(self):
        """Test relationships creation."""
        relationships = EntityRelationships()
        assert relationships.container is None
        assert len(relationships.contained_entities) == 0
        assert len(relationships.neighbors) == 0
        assert len(relationships.interactions) == 0
    
    def test_add_neighbor(self, biological_entity):
        """Test adding neighbor relationship."""
        relationships = EntityRelationships()
        relationships.add_neighbor(biological_entity, 50.0)
        
        assert biological_entity in relationships.neighbors
        assert relationships.neighbors[biological_entity] == 50.0
    
    def test_record_interaction(self, biological_entity):
        """Test recording interactions."""
        relationships = EntityRelationships()
        time = datetime.now()
        
        relationships.record_interaction(biological_entity, "division", time)
        
        assert len(relationships.interactions) == 1
        entity, interaction_type, timestamp = relationships.interactions[0]
        assert entity == biological_entity
        assert interaction_type == "division"
        assert timestamp == time


class TestBiologicalEntity:
    """Test biological entity functionality."""
    
    def test_creation(self, biological_entity):
        """Test entity creation."""
        assert biological_entity.entity_id == "cell_001"
        assert biological_entity.entity_type == EntityType.CELL
        assert biological_entity.natural_properties is not None
        assert biological_entity.experimental_properties is not None
        assert len(biological_entity.observation_history) == 0
    
    def test_age_calculation(self, biological_entity):
        """Test age calculation."""
        # Entity created 24 hours ago
        age = biological_entity.age
        assert 23.0 < age < 25.0  # Allow some tolerance for test execution time
    
    def test_add_observation(self, biological_entity):
        """Test adding observation."""
        observation = EntityObservation(
            entity_id="cell_001",
            timestamp=datetime.now(),
            position=(100, 200, 50),
            morphology=None,
            intensities={"DAPI": 1000},
            exposures={"DAPI": 50},
            quality_metrics={"confidence": 0.9},
            metadata={}
        )
        
        initial_count = len(biological_entity.observation_history)
        biological_entity.add_observation(observation)
        
        assert len(biological_entity.observation_history) == initial_count + 1
        assert biological_entity.observation_history[-1] == observation


class TestBiologicalSample:
    """Test biological sample functionality."""
    
    def test_creation(self):
        """Test sample creation."""
        sample = BiologicalSample("sample_001")
        
        assert sample.sample_id == "sample_001"
        assert len(sample.entities) == 0
        assert len(sample.conditions) == 0
    
    def test_add_entity(self, biological_entity):
        """Test adding entity to sample."""
        sample = BiologicalSample("sample_001")
        sample.add_entity(biological_entity)
        
        assert biological_entity.entity_id in sample.entities
        assert sample.entities[biological_entity.entity_id] == biological_entity
    
    def test_get_entities(self, biological_entity):
        """Test getting entities from sample."""
        sample = BiologicalSample("sample_001")
        sample.add_entity(biological_entity)
        
        # Get all entities
        all_entities = sample.get_entities()
        assert len(all_entities) == 1
        assert all_entities[0] == biological_entity
        
        # Get entities by type
        cell_entities = sample.get_entities(EntityType.CELL)
        assert len(cell_entities) == 1
        
        nucleus_entities = sample.get_entities(EntityType.NUCLEUS)
        assert len(nucleus_entities) == 0
    
    def test_update_condition(self):
        """Test updating sample conditions."""
        sample = BiologicalSample("sample_001")
        sample.update_condition("temperature", 37.0)
        sample.update_condition("pH", 7.4)
        
        assert sample.conditions["temperature"] == 37.0
        assert sample.conditions["pH"] == 7.4


class TestEntityObservation:
    """Test entity observation functionality."""
    
    def test_creation(self):
        """Test observation creation."""
        observation = EntityObservation(
            entity_id="cell_001",
            timestamp=datetime.now(),
            position=(100, 200, 50),
            morphology=None,
            intensities={"DAPI": 1000, "FITC": 500},
            exposures={"DAPI": 50, "FITC": 100},
            quality_metrics={"confidence": 0.9, "snr": 15.0},
            metadata={"experiment": "test"}
        )
        
        assert observation.entity_id == "cell_001"
        assert observation.position == (100, 200, 50)
        assert observation.intensities["DAPI"] == 1000
        assert observation.exposures["FITC"] == 100
        assert observation.quality_metrics["confidence"] == 0.9
        assert observation.metadata["experiment"] == "test"