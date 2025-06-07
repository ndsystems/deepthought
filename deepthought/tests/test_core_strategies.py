"""Test suite for core strategies."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from ..core.strategies import (
    CompositeStrategy,
    TrackDynamicsStrategy,
    MapSampleStrategy,
    FocusMapStrategy,
    MultiChannelAcquisitionStrategy,
    TimeSeriesWorkflow,
    SampleMappingWorkflow
)
from ..core.loop import (
    MicroscopeState,
    Perception,
    StagePosition,
    MoveStageTo,
    AcquireImage,
    AutoFocus,
    ObservationStrategy,
    Objective,
    LightPath
)
from ..domain.biology import BiologicalEntity, EntityType


@pytest.fixture
def microscope_state():
    """Create test microscope state."""
    return MicroscopeState(
        objective=Objective(60.0, 1.4, 0.17, False),
        stage=StagePosition(x=0, y=0, z=0),
        light_path=LightPath("DAPI", 50.0, 100.0, []),
        temperature=37.0
    )


@pytest.fixture
def perception():
    """Create test perception."""
    perception = Perception()
    # Add some test entities
    perception.spatial_context = {
        "cell_001": {"x": 100, "y": 200, "z": 50},
        "cell_002": {"x": 300, "y": 400, "z": 50}
    }
    perception.confidence = {
        "cell_001": 0.9,
        "cell_002": 0.7
    }
    perception.quality_metrics = {
        "(100, 200, 50)": 0.8,
        "(300, 400, 50)": 0.6
    }
    return perception


class MockStrategy(ObservationStrategy):
    """Mock strategy for testing composite behavior."""
    
    def __init__(self, name, actions=None, complete_after=2):
        self.name = name
        self.actions = actions or []
        self.complete_after = complete_after
        self.call_count = 0
    
    def next_action(self, perception: Perception):
        if self.call_count >= self.complete_after:
            return None
        
        self.call_count += 1
        if self.actions:
            return self.actions[(self.call_count - 1) % len(self.actions)]
        
        return MoveStageTo(StagePosition(x=self.call_count, y=0, z=0))
    
    def is_complete(self, perception: Perception) -> bool:
        return self.call_count >= self.complete_after


class TestCompositeStrategy:
    """Test composite strategy functionality."""
    
    def test_creation(self):
        """Test composite strategy creation."""
        strategies = [
            MockStrategy("first", complete_after=2),
            MockStrategy("second", complete_after=1)
        ]
        composite = CompositeStrategy(strategies)
        
        assert len(composite.strategies) == 2
        assert composite.current_index == 0
    
    def test_sequential_execution(self, perception):
        """Test sequential strategy execution."""
        strategies = [
            MockStrategy("first", complete_after=2),
            MockStrategy("second", complete_after=2)
        ]
        composite = CompositeStrategy(strategies)
        
        # Should execute first strategy
        action1 = composite.next_action(perception)
        assert action1 is not None
        assert strategies[0].call_count == 1
        assert strategies[1].call_count == 0
        
        action2 = composite.next_action(perception)
        assert action2 is not None
        assert strategies[0].call_count == 2
        assert strategies[1].call_count == 0
        
        # First strategy complete, should move to second
        action3 = composite.next_action(perception)
        assert action3 is not None
        assert strategies[0].call_count == 2
        assert strategies[1].call_count == 1
        
        action4 = composite.next_action(perception)
        assert action4 is not None
        assert strategies[1].call_count == 2
        
        # Both complete
        action5 = composite.next_action(perception)
        assert action5 is None
        assert composite.is_complete(perception)


class TestTrackDynamicsStrategy:
    """Test dynamics tracking strategy."""
    
    def test_creation(self):
        """Test strategy creation."""
        target_entities = {"cell_001", "cell_002"}
        strategy = TrackDynamicsStrategy(
            duration=timedelta(minutes=30),
            interval=timedelta(seconds=30),
            target_entities=target_entities
        )
        
        assert strategy.target_entities == target_entities
        assert len(strategy.next_observation) == 2
    
    def test_observation_scheduling(self, perception):
        """Test observation scheduling logic."""
        target_entities = {"cell_001"}
        strategy = TrackDynamicsStrategy(
            duration=timedelta(minutes=1),
            interval=timedelta(seconds=1),
            target_entities=target_entities
        )
        
        # Should provide action for due entity
        action = strategy.next_action(perception)
        assert isinstance(action, MoveStageTo)
        assert action.target.x == 100
        assert action.target.y == 200
    
    def test_completion_by_time(self):
        """Test completion based on duration."""
        strategy = TrackDynamicsStrategy(
            duration=timedelta(microseconds=1),  # Very short duration
            interval=timedelta(seconds=1),
            target_entities={"cell_001"}
        )
        
        # Should be complete immediately due to short duration
        assert strategy.is_complete(Perception())


class TestMapSampleStrategy:
    """Test sample mapping strategy."""
    
    def test_creation(self):
        """Test strategy creation."""
        center = StagePosition(x=500, y=500, z=0)
        strategy = MapSampleStrategy(
            center=center,
            size=(200, 200),
            resolution=50.0
        )
        
        assert strategy.center == center
        assert strategy.size == (200, 200)
        assert len(strategy.positions) > 0
    
    def test_position_generation(self):
        """Test grid position generation."""
        center = StagePosition(x=0, y=0, z=0)
        strategy = MapSampleStrategy(
            center=center,
            size=(100, 100),
            resolution=50.0
        )
        
        # Should generate a grid around center
        positions = strategy.positions
        assert len(positions) == 9  # 3x3 grid
        
        # Check that center is included
        center_found = any(
            abs(pos.x - 0) < 1 and abs(pos.y - 0) < 1 
            for pos in positions
        )
        assert center_found
    
    def test_mapping_workflow(self, perception):
        """Test mapping workflow execution."""
        center = StagePosition(x=0, y=0, z=0)
        strategy = MapSampleStrategy(
            center=center,
            size=(100, 100),
            resolution=100.0  # Single position
        )
        
        # Should provide move action
        action = strategy.next_action(perception)
        assert isinstance(action, MoveStageTo)
        
        # Mark position as visited
        strategy.visited.add(action.target)
        
        # Should be complete
        assert strategy.is_complete(perception)


class TestFocusMapStrategy:
    """Test focus mapping strategy."""
    
    def test_creation(self):
        """Test strategy creation."""
        positions = [
            StagePosition(x=0, y=0, z=0),
            StagePosition(x=100, y=100, z=0)
        ]
        strategy = FocusMapStrategy(positions, focus_range=20.0)
        
        assert strategy.positions == positions
        assert strategy.focus_range == 20.0
        assert len(strategy.focus_map) == 0
    
    def test_focus_workflow(self, perception):
        """Test focus mapping workflow."""
        positions = [StagePosition(x=0, y=0, z=0)]
        strategy = FocusMapStrategy(positions)
        
        # First action should be move
        action1 = strategy.next_action(perception)
        assert isinstance(action1, MoveStageTo)
        
        # Set current position
        strategy.current_position = positions[0]
        
        # Next action should be autofocus
        action2 = strategy.next_action(perception)
        assert isinstance(action2, AutoFocus)
        
        # Mark as focused
        strategy.focus_map[str(positions[0])] = 0.0
        
        # Should be complete
        assert strategy.is_complete(perception)


class TestMultiChannelAcquisitionStrategy:
    """Test multi-channel acquisition strategy."""
    
    def test_creation(self):
        """Test strategy creation."""
        channels = {"DAPI": 50.0, "FITC": 100.0}
        position = StagePosition(x=100, y=200, z=50)
        
        strategy = MultiChannelAcquisitionStrategy(channels, position)
        
        assert strategy.channels == channels
        assert strategy.position == position
        assert len(strategy.acquired) == 0
    
    def test_acquisition_workflow(self, perception):
        """Test acquisition workflow."""
        channels = {"DAPI": 50.0, "FITC": 100.0}
        position = StagePosition(x=100, y=200, z=50)
        
        strategy = MultiChannelAcquisitionStrategy(channels, position)
        
        # First action should be move to position
        action1 = strategy.next_action(perception)
        assert isinstance(action1, MoveStageTo)
        assert action1.target == position
        
        # Simulate being at position
        perception.spatial_context['current_position'] = position
        
        # Next actions should be acquisitions
        action2 = strategy.next_action(perception)
        assert isinstance(action2, AcquireImage)
        assert action2.channel in channels
        
        # Mark first channel as acquired
        strategy.acquired.add(action2.channel)
        
        # Should provide second channel
        action3 = strategy.next_action(perception)
        assert isinstance(action3, AcquireImage)
        assert action3.channel != action2.channel
        
        # Mark second channel as acquired
        strategy.acquired.add(action3.channel)
        
        # Should be complete
        assert strategy.is_complete(perception)


class TestWorkflows:
    """Test workflow classes."""
    
    @pytest.mark.asyncio
    async def test_sample_mapping_workflow(self, microscope_state):
        """Test sample mapping workflow."""
        workflow = SampleMappingWorkflow(
            center=StagePosition(x=0, y=0, z=0),
            size=(100, 100),
            resolution=100.0,
            channels={"DAPI": 50.0}
        )
        
        # This would normally run the full workflow
        # For testing, we just verify the structure
        assert workflow.center.x == 0
        assert workflow.size == (100, 100)
        assert workflow.channels == {"DAPI": 50.0}
    
    @pytest.mark.asyncio  
    async def test_time_series_workflow(self, microscope_state):
        """Test time series workflow."""
        workflow = TimeSeriesWorkflow(
            channels={"DAPI": 50.0},
            duration=timedelta(minutes=5),
            interval=timedelta(seconds=30),
            positions=[StagePosition(x=0, y=0, z=0)]
        )
        
        # Verify structure
        assert workflow.duration == timedelta(minutes=5)
        assert workflow.interval == timedelta(seconds=30)
        assert len(workflow.positions) == 1