from skimage import measure
import numpy as np
from coords import rc_to_cart

class SegmentedImage:
    # access all aspects of segmented image here.

    def __init__(self, image, label):
        self.image = image
        self.label = label
        self.regions = self.get_regions()

    def set_xy(self, stage_coords):
        # coordinate transformation from rc to cartesian
        for reg in self.regions:
            rc_coords = np.array([reg.centroid])
            coords, _ = rc_to_cart(rc_coords, image=self.image)
            x, y = coords[0]
            x = x * pixel_size
            y = y * pixel_size
            x_microns = np.around(x + stage_coords[0])
            y_microns = np.around(y + stage_coords[1])
            reg.xy = [x_microns, y_microns]

    def get_regions(self):
        # get individual label regions from image
        regions = measure.regionprops(self.label, intensity_image=self.image)
        return regions


class Labeller:
    def __init__(self, image, model):
        self.model = model
        self.image = image
        self.label = self.generate_label(image)
        self.result = SegmentedImage(self.image, self.label)

    def generate_label(self, image):
        return self.model.detect(image)    