"""
Sample definitions for different microscopy containers.
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

@dataclass
class Well:
    """Represents a single well in a multi-well plate."""
    center: Tuple[float, float]  # Center coordinates (x, y) in µm
    diameter: float  # Well diameter in µm
    depth: float  # Well depth in µm
    max_volume: float  # Maximum volume in µL

@dataclass
class ConfocalDish:
    """35mm confocal dish commonly used for cell culture and imaging."""
    center: Tuple[float, float] = (0, 0)  # Center coordinates (x, y) in µm
    diameter: float = 35000  # 35mm converted to µm
    depth: float = 2000  # 2mm depth in µm
    glass_thickness: float = 170  # Standard #1.5 coverslip thickness in µm
    working_volume: float = 2000  # Typical working volume in µL
    
    @property
    def radius(self) -> float:
        """Get the radius of the dish."""
        return self.diameter / 2
    
    def is_point_inside(self, point: Tuple[float, float]) -> bool:
        """Check if a point lies within the dish area."""
        x, y = point
        cx, cy = self.center
        return (x - cx)**2 + (y - cy)**2 <= self.radius**2

@dataclass
class WellPlate:
    """Base class for multi-well plates."""
    rows: int
    columns: int
    well_spacing: float  # Center-to-center distance in µm
    well_diameter: float  # Well diameter in µm
    well_depth: float = 11000  # Standard well depth ~11mm
    plate_height: float = 14000  # Standard plate height ~14mm
    origin: Tuple[float, float] = (0, 0)  # Top-left corner coordinates
    
    def get_well_position(self, row: int, col: int) -> Tuple[float, float]:
        """Get the center coordinates of a specific well."""
        if not (0 <= row < self.rows and 0 <= col < self.columns):
            raise ValueError(f"Invalid well position: row={row}, col={col}")
        
        x = self.origin[0] + (col + 0.5) * self.well_spacing
        y = self.origin[1] + (row + 0.5) * self.well_spacing
        return (x, y)
    
    def get_all_well_positions(self) -> List[Tuple[float, float]]:
        """Get coordinates for all wells in the plate."""
        positions = []
        for row in range(self.rows):
            for col in range(self.columns):
                positions.append(self.get_well_position(row, col))
        return positions

class Plate96Well(WellPlate):
    """Standard 96-well plate."""
    def __init__(self, origin: Tuple[float, float] = (0, 0)):
        super().__init__(
            rows=8,
            columns=12,
            well_spacing=9000,  # 9mm in µm
            well_diameter=6400,  # 6.4mm in µm
            origin=origin
        )
        self.well_volume = 360  # Maximum well volume in µL
        self.working_volume = 200  # Typical working volume in µL

class Plate6Well(WellPlate):
    """Standard 6-well plate."""
    def __init__(self, origin: Tuple[float, float] = (0, 0)):
        super().__init__(
            rows=2,
            columns=3,
            well_spacing=39200,  # 39.2mm in µm
            well_diameter=34800,  # 34.8mm in µm
            origin=origin
        )
        self.well_volume = 17100  # Maximum well volume in µL
        self.working_volume = 3000  # Typical working volume in µL
