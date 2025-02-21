"""
Detection module for microscopy image analysis.

This module provides detectors for identifying and analyzing objects in microscopy images.
Currently supports nuclear detection using the Cellpose model.
"""

from typing import List, Tuple, Optional
import numpy as np
from cellpose import models

# Constants for nuclear detection
DEFAULT_GPU: int = 1
DEFAULT_NUCLEAR_DIAMETER: int = 100  # Diameter in pixels for typical nuclei
DEFAULT_CHANNELS: Tuple[int, int] = (0, 0)  # Grayscale nuclear channel configuration

class NuclearDetector:
    """Nuclear detector using Cellpose model.
    
    This class provides functionality to detect cell nuclei in microscopy images
    using the Cellpose deep learning model. It is optimized for fluorescence
    microscopy images of cell nuclei.
    
    Attributes:
        gpu (int): Whether to use GPU acceleration (1) or not (0)
        diameter (int): Expected diameter of nuclei in pixels
        model (models.Cellpose): Cellpose model instance
    """
    
    def __init__(self, 
                 gpu: int = DEFAULT_GPU,
                 diameter: int = DEFAULT_NUCLEAR_DIAMETER):
        """Initialize nuclear detector.
        
        Args:
            gpu: Whether to use GPU acceleration (1) or not (0)
            diameter: Expected diameter of nuclei in pixels
        """
        self.gpu = gpu
        self.diameter = diameter
        self.model = self._create_model()
    
    def _create_model(self) -> models.Cellpose:
        """Create and configure the Cellpose model.
        
        Returns:
            Configured Cellpose model instance
        """
        return models.Cellpose(gpu=self.gpu, model_type='nuclei')
    
    def detect(self, image: np.ndarray) -> np.ndarray:
        """Detect nuclei in the input image.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Label map where each nucleus has a unique integer ID
        """
        output = self.model.eval([image], 
                               channels=DEFAULT_CHANNELS,
                               diameter=self.diameter)
        return output[0][0]  # First image, first channel
    
    def get_object_properties(self, label_map: np.ndarray) -> List[dict]:
        """Extract properties of detected nuclei.
        
        Args:
            label_map: Label map from detect() method
            
        Returns:
            List of dictionaries containing properties for each nucleus
        """
        props = []
        for label_id in np.unique(label_map)[1:]:  # Skip background (0)
            mask = label_map == label_id
            coords = np.where(mask)
            props.append({
                'label': int(label_id),
                'centroid': (float(np.mean(coords[0])), float(np.mean(coords[1]))),
                'area': int(np.sum(mask)),
                'bbox': (
                    int(np.min(coords[1])),  # x_min
                    int(np.min(coords[0])),  # y_min
                    int(np.max(coords[1])),  # x_max
                    int(np.max(coords[0]))   # y_max
                )
            })
        return props
