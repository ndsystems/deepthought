"""Test suite for core action-perception loop."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from ..core.loop import (
    MicroscopyLoop,
    MicroscopeAction,
    MicroscopeState,
    Perception,
    StagePosition,
    ActionStatus,
    ActionResult,
    ActionContext,
    MoveStageTo,
    AcquireImage,
    AutoFocus,
    ObservationStrategy,
    Objective,
    LightPath
)
from ..domain.observation import TechnicalParameters
from ..domain.biology import BiologicalEntity, EntityType


@pytest.fixture
def stage_position():
    """Create test stage position."""
    return StagePosition(x=100.0, y=200.0, z=50.0)


@pytest.fixture
def objective():
    """Create test objective."""
    return Objective(
        magnification=60.0,
        numerical_aperture=1.4,
        working_distance=0.17,
        is_air=False
    )


@pytest.fixture
def light_path():
    """Create test light path."""
    return LightPath(
        source="488nm_laser",
        intensity=50.0,
        exposure=100.0,
        filters=["GFP", "bandpass"]
    )


@pytest.fixture
def microscope_state(stage_position, objective, light_path):
    """Create test microscope state."""
    return MicroscopeState(
        objective=objective,
        stage=stage_position,
        light_path=light_path,
        temperature=37.0,
        last_action=None
    )


@pytest.fixture
def technical_params():
    """Create test technical parameters."""
    return TechnicalParameters(
        pixel_size=0.1,
        time_resolution=0.1,
        channels={"DAPI": {"exposure": 50, "laser_power": 10}},
        exposure_times={"DAPI": 50},
        laser_powers={"488nm": 10},
        gain={"camera": 1.0}
    )


@pytest.fixture
def action_context(microscope_state, technical_params):
    """Create test action context."""
    return ActionContext(
        microscope_state=microscope_state,
        technical_params=technical_params,
        timestamp=datetime.now(),
        metadata={"test": True}
    )


class MockStrategy(ObservationStrategy):
    """Mock strategy for testing."""
    
    def __init__(self, actions=None, complete_after=3):
        self.actions = actions or []
        self.complete_after = complete_after
        self.call_count = 0
    
    def next_action(self, perception: Perception) -> MicroscopeAction:
        if self.call_count >= self.complete_after:
            return None
        
        self.call_count += 1
        if self.actions:
            return self.actions[(self.call_count - 1) % len(self.actions)]
        
        # Default action
        return MoveStageTo(StagePosition(x=self.call_count, y=0, z=0))
    
    def is_complete(self, perception: Perception) -> bool:
        return self.call_count >= self.complete_after


class TestStagePosition:
    """Test stage position functionality."""
    
    def test_creation(self, stage_position):
        """Test stage position creation."""
        assert stage_position.x == 100.0
        assert stage_position.y == 200.0
        assert stage_position.z == 50.0


class TestMicroscopeState:
    """Test microscope state functionality."""
    
    def test_creation(self, microscope_state):
        """Test microscope state creation."""
        assert microscope_state.objective.magnification == 60.0
        assert microscope_state.stage.x == 100.0
        assert microscope_state.temperature == 37.0
        assert microscope_state.last_action is None
    
    def test_can_execute(self, microscope_state):
        """Test action validation."""
        action = MoveStageTo(StagePosition(x=0, y=0, z=0))
        assert microscope_state.can_execute(action)
    
    def test_predict_next_state(self, microscope_state):
        """Test state prediction."""
        new_position = StagePosition(x=300, y=400, z=60)
        action = MoveStageTo(new_position)
        
        predicted_state = microscope_state.predict_next_state(action)
        assert predicted_state.stage.x == 300
        assert predicted_state.stage.y == 400
        assert predicted_state.last_action == "move_stage"


class TestActions:
    """Test microscope actions."""
    
    @pytest.mark.asyncio
    async def test_move_stage_action(self, action_context):
        """Test stage movement action."""
        target = StagePosition(x=500, y=600, z=70)
        action = MoveStageTo(target)
        
        result = await action.execute(action_context)
        
        assert result.status == ActionStatus.COMPLETED
        assert result.data['position'] == target
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_acquire_image_action(self, action_context):
        """Test image acquisition action."""
        action = AcquireImage(exposure=100.0, channel="DAPI")
        
        result = await action.execute(action_context)
        
        assert result.status == ActionStatus.COMPLETED
        assert result.data['exposure'] == 100.0
        assert result.data['channel'] == "DAPI"
        assert result.energy_cost == 100.0
        assert 'image' in result.data
    
    @pytest.mark.asyncio
    async def test_autofocus_action(self, action_context):
        """Test autofocus action."""
        action = AutoFocus(range_um=20.0, steps=15)
        
        result = await action.execute(action_context)
        
        assert result.status == ActionStatus.COMPLETED
        assert 'focus_position' in result.data
    
    def test_action_validation(self, microscope_state):
        """Test action validation logic."""
        # Valid movement
        action = MoveStageTo(StagePosition(x=0, y=0, z=0))
        assert action.validate(microscope_state)
        
        # Valid acquisition
        microscope_state.light_path.source = "DAPI"
        action = AcquireImage(exposure=50.0, channel="DAPI")
        assert action.validate(microscope_state)
        
        # Invalid acquisition (wrong channel)
        action = AcquireImage(exposure=50.0, channel="FITC")
        assert not action.validate(microscope_state)


class TestPerception:
    """Test perception functionality."""
    
    def test_creation(self):
        """Test perception creation."""
        perception = Perception()
        assert len(perception.entities) == 0
        assert len(perception.confidence) == 0
        assert len(perception.spatial_context) == 0
        assert len(perception.quality_metrics) == 0
    
    def test_update_perception(self):
        """Test perception update with observation."""
        from ..domain.observation import EntityObservation
        
        perception = Perception()
        observation = EntityObservation(
            entity_id="cell_001",
            timestamp=datetime.now(),
            position=(100, 200, 50),
            morphology=None,
            intensities={"DAPI": 1000},
            exposures={"DAPI": 50},
            quality_metrics={"detection_confidence": 0.9},
            metadata={}
        )
        
        perception.update(observation)
        
        assert "cell_001" in perception.confidence
        assert perception.confidence["cell_001"] == 0.9
        assert "cell_001" in perception.spatial_context
        assert perception.spatial_context["cell_001"] == (100, 200, 50)


class TestMicroscopyLoop:
    """Test microscopy loop functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_loop(self, microscope_state):
        """Test basic loop execution."""
        strategy = MockStrategy(complete_after=2)
        loop = MicroscopyLoop(strategy, microscope_state)
        
        perception = await loop.run()
        
        assert isinstance(perception, Perception)
        assert strategy.call_count == 2
    
    @pytest.mark.asyncio
    async def test_loop_with_actions(self, microscope_state):
        """Test loop with specific actions."""
        actions = [
            MoveStageTo(StagePosition(x=100, y=100, z=0)),
            AcquireImage(exposure=50.0, channel="DAPI"),
            AutoFocus(range_um=10.0)
        ]
        
        strategy = MockStrategy(actions=actions, complete_after=3)
        loop = MicroscopyLoop(strategy, microscope_state)
        
        perception = await loop.run()
        
        assert isinstance(perception, Perception)
        assert strategy.call_count == 3
    
    @pytest.mark.asyncio
    async def test_loop_invalid_action(self, microscope_state):
        """Test loop with invalid action."""
        # Create an action that will fail validation
        invalid_action = AcquireImage(exposure=50.0, channel="WRONG_CHANNEL")
        strategy = MockStrategy(actions=[invalid_action])
        loop = MicroscopyLoop(strategy, microscope_state)
        
        with pytest.raises(ValueError, match="Invalid action"):
            await loop.run()
    
    @pytest.mark.asyncio
    async def test_loop_state_updates(self, microscope_state):
        """Test that loop updates state correctly."""
        target_position = StagePosition(x=999, y=888, z=777)
        action = MoveStageTo(target_position)
        strategy = MockStrategy(actions=[action], complete_after=1)
        
        loop = MicroscopyLoop(strategy, microscope_state)
        await loop.run()
        
        # State should be updated
        assert loop.state.stage.x == 999
        assert loop.state.stage.y == 888
        assert loop.state.last_action == "move_stage"


class TestObservationStrategy:
    """Test observation strategy interface."""
    
    def test_mock_strategy(self):
        """Test mock strategy functionality."""
        strategy = MockStrategy(complete_after=5)
        perception = Perception()
        
        # Should provide actions until complete
        for i in range(5):
            action = strategy.next_action(perception)
            assert action is not None
            assert not strategy.is_complete(perception)
        
        # Should be complete after specified number
        assert strategy.is_complete(perception)
        
        # Should return None when complete
        action = strategy.next_action(perception)
        assert action is None