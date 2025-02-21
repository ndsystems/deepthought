# deepthought

A domain-driven microscopy automation library built on an action-perception loop architecture, integrating with Bluesky and Micro-Manager for intelligent microscopy experiments.

## Features

### Core Architecture

- **Action-Perception Loop**: Natural workflow that matches how microscopists work
  - Atomic actions with state validation
  - Incremental perception updates
  - Adaptive decision making
  - Real-time visualization

- **Composable Strategies**
  - Cell tracking
  - Sample mapping
  - Multi-channel acquisition
  - Focus mapping
  - Dynamic adaptation

- **Flexible Workflows**
  - Cell tracking experiments
  - Tissue mapping
  - Multi-modal imaging
  - Adaptive protocols

### Technical Features

- Clean hardware abstraction layer for microscope devices
- Bluesky integration for experiment tracking and data management
- Real-time visualization with quality metrics
- Built-in image processing and analysis

## Installation

### Option 1: Using pip with virtualenv (recommended)

```bash
# Create and activate virtual environment
python -m pip install virtualenv
python -m virtualenv deepthought
source deepthought/bin/activate  # On Windows: deepthought\Scripts\activate

# Install package
python -m pip install -U pip
python -m pip install -e .
```

### Option 2: Direct installation

```bash
python -m pip install -e .
```

## Quick Start

### Basic Cell Tracking Experiment

```python
from deepthought.microscopy_workflows import CellTrackingExperiment
from deepthought.microscope import ActionPerceptionMicroscope
from datetime import timedelta

# Initialize microscope
microscope = ActionPerceptionMicroscope(mmc)  # assuming mmc is available

# Configure experiment
experiment = CellTrackingExperiment(
    duration=timedelta(hours=1),
    interval=timedelta(seconds=30),
    channels={
        "DAPI": 30,    # ms exposure
        "FITC": 200,   # ms exposure
        "TxRed": 200   # ms exposure
    },
    target_cell_type="cell",
    min_cells=10
)

# Run experiment
results = await experiment.run(initial_state)
```

### Custom Strategy Implementation

```python
from deepthought.microscopy_loop import ObservationStrategy, MicroscopeAction

class CustomStrategy(ObservationStrategy):
    """Example custom observation strategy"""
    
    def next_action(self, perception):
        # Make decisions based on current perception
        if not perception.has_focus():
            return AutoFocusAction()
            
        if perception.needs_new_position():
            return MoveStageTo(self.next_position())
            
        return AcquireImageAction(self.current_channel())
    
    def is_complete(self, perception):
        return self.goals_achieved(perception)
```

### Real-time Visualization

```python
from deepthought.run import ActionPerceptionViewer

# Create viewer
viewer = ActionPerceptionViewer()

# Update callback
async def update_view(perception):
    viewer.update_perception(perception)
    # Shows:
    # - Detected cells
    # - Current field of view
    # - Quality metrics
    await asyncio.sleep(0.1)

# Run experiment with visualization
experiment.run(callback=update_view)
```

## Version

Current version: 2.0.0-alpha.0

DeepThought follows [Semantic Versioning](https://semver.org/) with additional alpha/beta release designations:

- Version format: `MAJOR.MINOR.PATCH-RELEASE_TYPE.NUMBER`
  - `MAJOR`: Incompatible API changes
  - `MINOR`: New features in a backward compatible manner
  - `PATCH`: Backward compatible bug fixes
  - `RELEASE_TYPE`: alpha/beta/rc/final
  - `NUMBER`: Sub-version for alpha/beta releases (0, 1, 2, etc.)

Examples:
- `2.0.0-alpha.0`: First alpha release of version 2.0.0
- `2.0.0-alpha.1`: Second alpha release with improvements
- `2.0.0-beta.0`: First beta release
- `2.0.0`: Final release

## Project Structure

```
deepthought/
├── microscopy_loop.py     # Core action-perception loop
├── microscopy_strategies.py  # Observation strategies
├── microscopy_workflows.py   # High-level experiments
├── microscope.py         # Hardware interface
├── observation.py        # Perception management
├── biology.py           # Biological entity models
└── run.py              # Main entry point
```

## Architecture Overview

### Action-Perception Loop

The system operates on a continuous loop of:
1. **Observe**: Gather data about the current state
2. **Perceive**: Update understanding of the sample
3. **Decide**: Choose next action based on current perception
4. **Act**: Execute chosen action
5. **Validate**: Ensure action completed successfully

### Strategies

Strategies are composable and can be combined for complex experiments:

```python
strategy = CompositeStrategy([
    FocusMapStrategy(positions),
    MapSampleStrategy(center, size),
    MultiChannelAcquisitionStrategy(channels)
])
```

### Bluesky Integration

All actions and perceptions are logged to Bluesky's database:
- Experiment metadata
- Action history with parameters and results
- Perception state evolution
- Quality metrics


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

For licensing inquiries, please contact: pskeshu@gmail.com
