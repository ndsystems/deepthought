"""Configuration management for microscope automation system."""

import yaml
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
import logging
from logging.handlers import RotatingFileHandler

@dataclass
class MicroscopeConfig:
    """Hardware configuration for microscopes."""
    name: str
    ip_address: str
    pixel_size: float
    max_exposure: float
    objective_magnifications: Dict[int, float]

@dataclass
class SystemConfig:
    """System-wide configuration."""
    log_dir: Path
    data_dir: Path
    max_memory_usage: int  # MB
    debug_mode: bool

class ConfigManager:
    """Manages system configuration and logging setup."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._setup_logging()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path) as f:
            return yaml.safe_load(f)
            
    def _setup_logging(self) -> None:
        """Configure logging system."""
        log_dir = Path(self.config["system"]["log_dir"])
        log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_dir / "microscope.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(levelname)s: %(message)s'
        ))
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    def get_microscope_config(self, name: str) -> MicroscopeConfig:
        """Get configuration for specific microscope."""
        if name not in self.config["microscopes"]:
            raise ValueError(f"Microscope {name} not found in configuration")
            
        scope_config = self.config["microscopes"][name]
        return MicroscopeConfig(**scope_config)
        
    def get_system_config(self) -> SystemConfig:
        """Get system-wide configuration."""
        return SystemConfig(**self.config["system"]) 