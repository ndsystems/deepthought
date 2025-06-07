"""System monitoring and performance tracking."""

import time
import psutil
import logging
from typing import Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    duration: float
    memory_usage: float
    cpu_usage: float
    
class SystemMonitor:
    """Monitors system resources and performance."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.process = psutil.Process()
        
    @contextmanager
    def measure_performance(self, operation: str):
        """Context manager to measure operation performance."""
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            end_memory = self.process.memory_info().rss / 1024 / 1024
            cpu_percent = self.process.cpu_percent()
            
            metrics = PerformanceMetrics(
                duration=duration,
                memory_usage=end_memory - start_memory,
                cpu_usage=cpu_percent
            )
            
            self.logger.info(
                f"Operation: {operation}, "
                f"Duration: {duration:.2f}s, "
                f"Memory Delta: {metrics.memory_usage:.2f}MB, "
                f"CPU Usage: {metrics.cpu_usage:.1f}%"
            ) 