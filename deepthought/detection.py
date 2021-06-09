import numpy as np
from cellpose import models
from bluesky.callbacks import broker
from skimage import measure
from viz import imshow
from compute import circularity, unit_pixel_length


def segment(image, kind):
    """Segment nuclei or cyto from image using cellpose and return the label"""
    model = models.Cellpose(gpu=0, model_type=kind)

    output = model.eval([image], channels=[0, 0])

    list_of_labels = output[0]
    return list_of_labels[0]


def find_object_properties(label, image):
    regions = measure.regionprops(label, intensity_image=image)
    return regions


def calculate_stage_coordinates(object_properties, stage_coords):
    stage_coords = np.array(stage_coords)

    x, y = object_properties["centroid-0"], object_properties["centroid-1"]

    x = unit_pixel_length() * x
    y = unit_pixel_length() * y

    x = np.around(x + stage_coords[0])
    y = np.around(y + stage_coords[1])

    object_properties["xy"] = list(zip(x, y))
    return object_properties
