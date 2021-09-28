from compute import circularity, axial_length
from viz import imshow
from skimage import measure
from bluesky.callbacks import broker
from cellpose import models
import logging
logging.getLogger("cellpose").setLevel(logging.WARNING)
import numpy as np
from coords import rc_to_cart

def segment(image, **kwargs):
    """Segment nuclei or cyto from image using cellpose and return the label"""
    kind = kwargs.get("kind")
    diameter = kwargs.get("diameter")

    model = models.Cellpose(gpu=1, model_type=kind)

    output = model.eval([image], channels=[0, 0], diameter=diameter)

    list_of_labels = output[0]
    return list_of_labels[0]


def find_object_properties(label, image, stage_coords, pixel_size):
    regions = measure.regionprops(label, intensity_image=image)

    # pixel coords
    for reg in regions:
        rc_coords = np.array([reg.centroid])
        
        coords, _ = rc_to_cart(rc_coords, image=image)
        x, y = coords[0]

        x = x * pixel_size
        y = y * pixel_size

        x_microns = np.around(x + stage_coords[0])
        y_microns = np.around(y + stage_coords[1])

        reg.xy = [x_microns, y_microns]
    
    return regions
