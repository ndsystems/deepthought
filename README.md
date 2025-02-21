# deepthought

A domain-driven microscopy automation library built on Bluesky and Micro-Manager for automated microscopy experiments.

## Features

- Clean hardware abstraction layer for microscope devices
- Flexible experiment planning and acquisition
- Built-in image processing and analysis
- Integration with Bluesky's RunEngine and DataBroker
- Real-time visualization and monitoring

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

```python
from deepthought.microscope import Microscope, MicroscopeConfig
from bluesky import RunEngine

# Initialize microscope with Micro-Manager core
microscope = Microscope(mmc)  # assuming mmc (Micro-Manager core) is available

# Optional: Customize microscope configuration
microscope.config = MicroscopeConfig(
    detector_pixel_size=6.5,  # um for Andor Zyla
    max_exposure=5000,  # ms
    exposure_target=0.5
)

# Option 1: Direct usage
# This will generate a plan and run it internally
grid_scan = microscope.grid_scan(
    channels=["DAPI", "RFP"],
    grid=(3, 3),  # 3x3 grid
    settle_time=0.1  # wait 100ms between positions
)

# Option 2: Use with Bluesky's RunEngine
# This gives you more control over execution and data collection
RE = RunEngine({})
plan = microscope.plans.grid_scan(
    microscope,
    channels=["DAPI", "RFP"],
    grid=(3, 3),
    settle_time=0.1
)
RE(plan)

# Auto-focus and exposure optimization are also available as plans
RE(microscope.auto_focus())
RE(microscope.auto_exposure())
```

## Data Access

The library uses databroker for data management. To access experimental data:

1. Configure databroker catalog:
   ```bash
   # Find databroker config location
   python -c "import databroker; print(databroker.catalog_search_path())"
   
   # Copy and edit catalog configuration
   cp ./catalog.yml /path/to/databroker/config/
   ```

2. Access data programmatically:
   ```python
   from microscope.storage import db
   
   # Get latest experiment
   header = db[-1]
   
   # Access data as pandas DataFrame
   df = header.table()
   ```

## Project Structure

```
microscope/
├── hardware/      # Device control and hardware interfaces
├── acquisition/   # Experiment planning and execution
├── analysis/      # Image processing and object detection
├── config/        # Configuration management
├── storage/       # Data access and persistence
└── visualization/ # Real-time display and results viewing
```

## Troubleshooting

- **LLVM Issues**: If you encounter errors with `llvmlite` (required by `numba`) and have `llvm11` installed, downgrade to `llvm10`.
- For more troubleshooting tips, see our [documentation](docs/troubleshooting.md).

