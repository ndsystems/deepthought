"""Command line interface for deepthought."""

from .run import (
    main,
    setup_channels,
    setup_microscopes,
    configure_run_engine,
    run_experiment
)

__all__ = [
    'main',
    'setup_channels',
    'setup_microscopes', 
    'configure_run_engine',
    'run_experiment'
]