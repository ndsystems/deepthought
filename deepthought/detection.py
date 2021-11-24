from skimage import measure
from cellpose import models
import numpy as np
from coords import rc_to_cart

class SegmentedImage:
    # access all aspects of segmented image here.

    def __init__(self, image, label):
        self.image = image
        self.label = label
        self.get_regions()

    def set_xy(self, stage_coords):
        # coordinate transformation from rc to cartesian
        for reg in self.regions:
            rc_coords = np.array([reg.centroid])
            
            coords, _ = rc_to_cart(rc_coords, image=image)
            x, y = coords[0]

            x = x * pixel_size
            y = y * pixel_size

            x_microns = np.around(x + stage_coords[0])
            y_microns = np.around(y + stage_coords[1])

            reg.xy = [x_microns, y_microns]

    def get_regions(self):
        # get individual label regions from image
        regions = measure.regionprops(self.label, intensity_image=self.image)
        self.regions = regions


def detect_using_cellpose(image, kind="nuclei", diameter=None):
    # define a cellpose model
    model = models.Cellpose(gpu=1, model_type=kind)
    # evaluate the result and return label
    output = model.eval([image], channels=[0, 0], diameter=diameter)
    list_of_labels = output[0]
    labelled_image = list_of_labels[0]
    return labelled_image    

def detect(image, **kwargs):
    # generate a label using a detection system
    label = segment_cellpose(image, **kwargs)
    # put the result in a special object and return
    result = SegmentedImage(image=image, label=label)
    return result

    