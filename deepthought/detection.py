from compute import circularity, axial_length
from viz import imshow
from skimage import measure
from bluesky.callbacks import broker
from cellpose import models
import numpy as np
import logging
logging.getLogger("cellpose").setLevel(logging.WARNING)


def segment(image, **kwargs):
    """Segment nuclei or cyto from image using cellpose and return the label"""
    kind = kwargs.get("kind")
    diameter = kwargs.get("diameter")

    model = models.Cellpose(gpu=0, model_type=kind)

    output = model.eval([image], channels=[0, 0], diameter=diameter)

    list_of_labels = output[0]
    return list_of_labels[0]


def find_object_properties(label, image):
    regions = measure.regionprops(label, intensity_image=image)
    return regions


def calculate_stage_coordinates(object_properties, stage_coords):
    stage_coords = np.array(stage_coords)

    x, y = object_properties["centroid-0"], object_properties["centroid-1"]

    x = axial_length(mag=60, binning=4, num_px=512) * x
    y = axial_length(mag=60, binning=4, num_px=512) * y

    x = np.around(x + stage_coords[0])
    y = np.around(y + stage_coords[1])

    object_properties["xy"] = list(zip(x, y))
    return object_properties
