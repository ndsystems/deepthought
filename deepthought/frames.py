# model describing unit data from the microscope

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Protocol
import numpy as np
from collections import OrderedDict

from labels import Labeller, LabelledImage
from detection import AnisotropyFrameDetector, NuclearDetector
from utils import pad_images_similar
from compute import calculate_anisotropy
from transform import register
from view import view
from coords import rc_to_cart
import pandas as pd
from data import db
from process import clear_border

@dataclass
class FrameMetadata:
    """Metadata for microscopy frames."""
    coords: Tuple[float, float]
    pixel_size: float
    channel: Optional[str] = None

@dataclass
class DetectedObject:
    """Representation of a detected microscopy object."""
    coords: np.ndarray
    intensity_data: Dict[str, np.ndarray]
    properties: Dict[str, any]

    def __init__(self):
        self.vector = OrderedDict()
        self.raster = OrderedDict()

class ObjectCollection:
    """Efficient collection of detected objects."""
    
    def __init__(self, channel: str, regions: List):
        self.channel = channel
        self.detected_objects: List[DetectedObject] = []
        self._process_regions(regions)

    def _process_regions(self, regions: List) -> None:
        """Process regions into detected objects."""
        for region in regions:
            obj = self._region_to_object(region)
            self.detected_objects.append(obj)

    def _region_to_object(self, region) -> DetectedObject:
        """Convert region to DetectedObject."""
        obj = DetectedObject()
        obj.raster[self.channel] = region.intensity_image
        obj.vector["coords"] = region.xy
        return obj

    def merge_secondary(self, other: 'ObjectCollection') -> None:
        """Merge secondary channel data into primary objects."""
        for primary, secondary in zip(self.detected_objects, other.detected_objects):
            primary.raster.update(secondary.raster)

class Frame:
    """Base class for microscopy frames."""

    def __init__(self, 
                 image: np.ndarray, 
                 coords: Tuple[float, float],
                 channel: str,
                 pixel_size: float):
        self.image = image
        self.metadata = FrameMetadata(
            coords=coords,
            pixel_size=pixel_size,
            channel=channel
        )
        self.channel = channel

    def clean_up(self) -> None:
        """Release frame resources."""
        if hasattr(self, 'image'):
            del self.image

    def get_label(self) -> np.ndarray:
        """Get frame label mask."""
        detector = self.channel.detector
        frame_label = Labeller(self.image, detector).make()
        return clear_border(frame_label)

    def get_objects(self, frame_label: np.ndarray) -> ObjectCollection:
        """Extract objects from frame using label mask."""
        regions = LabelledImage(self.image, frame_label).get_regions()
        regions = self._correct_object_coordinates(regions)
        return ObjectCollection(channel=self.channel, regions=regions)

    def _correct_object_coordinates(self, regions: List) -> List:
        """Transform region coordinates to global space."""
        for reg in regions:
            rc_coords = np.array([reg.centroid])
            coords, _ = rc_to_cart(rc_coords, image=self.image)
            x, y = coords[0]
            x = x * self.metadata.pixel_size
            y = y * self.metadata.pixel_size
            reg.xy = [
                round(x + self.metadata.coords[0]),
                round(y + self.metadata.coords[1])
            ]
        return regions

class FrameCollection:
    """Base class for frame collections."""

    def __init__(self):
        self.frames: List[Frame] = []

    def add_frame(self, frame: Frame) -> None:
        self.frames.append(frame)

class SingleLabelFrames(FrameCollection):
    """Collection of frames sharing a primary label."""

    def get_objects(self) -> ObjectCollection:
        """Process frames and extract objects."""
        primary_frame = self.frames[0]
        primary_label = primary_frame.get_label()
        primary_objects = primary_frame.get_objects(primary_label)

        for frame in self.frames[1:]:
            secondary_objects = frame.get_objects(primary_label)
            primary_objects.merge_secondary(secondary_objects)

        return primary_objects

class ObjectsAlbum:
    """Collection of object collections across multiple acquisitions."""

    def __init__(self):
        self.collection_groups: Dict[str, ObjectCollection] = OrderedDict()
        self.detected_objects: List[DetectedObject] = []
        self.count: int = 0

    def add_collection(self, uid: str, collection: ObjectCollection) -> None:
        """Add object collection to album."""
        self.collection_groups[uid] = collection
        self.count += len(collection.detected_objects)
        self.detected_objects.extend(collection.detected_objects)

    def __getitem__(self, index: int) -> DetectedObject:
        return self.detected_objects[index]

    def get_data_from_uid(self, uid: str) -> np.ndarray:
        """Retrieve raw data for given UID."""
        table = db[uid].table()
        return np.stack(table["image"].to_numpy())

    def view_raw(self, index: int) -> None:
        """View raw data for collection at index."""
        uid = list(self.collection_groups.keys())[index]
        img = self.get_data_from_uid(uid)
        view(img)

    def get_coords(self):
        coords = []

        for uid, objects_collection in self.collection_groups.items():
            coords.extend(
                [
                    detected_obj.vector["coords"]
                    for detected_obj in objects_collection.detected_objects
                ]
            )

        return coords


class AnisotropyFrame(Frame):
    """basic unit of anisotropy imaging frame"""

    def __init__(self, image, coords, model=None):
        if model is None:
            model = AnisotropyFrameDetector()

        super().__init__(image, coords, model)
        self.get_objects()

    def get_objects(self):
        # This currently does not currently get_objects
        self.label = Labeller(self.image, self.model)

        self.parallel = self.label.result.objects[0].intensity_image
        self.perpendicular = self.label.result.objects[1].intensity_image

        self.parallel, self.perpendicular = pad_images_similar(
            self.parallel, self.perpendicular
        )

        self.perpendicular = register(self.parallel, self.perpendicular)

        self.amap = calculate_anisotropy(self.parallel, self.perpendicular)

    def view(self):
        v = napari.Viewer()
        layer = v.add_image(self.parallel)
        v.add_image(self.amap, colormap="jet", contrast_limits=[0.01, 0.28])

    def read(self):
        values = [self.parallel, self.amap]
        keys = ["image", "anisotropy"]

        data = OrderedDict()

        for key, value in zip(keys, values):
            data[key] = value

        return data


class CellularFrame(Frame):
    def __init__(self, image, coords, channel):
        super().__init__(image, coords, channel)
