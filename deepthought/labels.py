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
            coords, _ = rc_to_cart(rc_coords, image=self.image)
            x, y = coords[0]
            x = x * pixel_size
            y = y * pixel_size
            x_microns = np.around(x + stage_coords[0])
            y_microns = np.around(y + stage_coords[1])
            reg.xy = [x_microns, y_microns]

    def get_regions(self):
        # get individual label regions from image
        self.regions = measure.regionprops(self.label, intensity_image=self.image)
        return self.regions


class NuclearLabel:
    def __init__(self, image):
        self.name = "cellpose"
        self.type = "nuclei"
        self.gpu = 1
        self.image = image
        self.create_model()
    
    def create_model(self):
        # define a cellpose model
        self.model = models.Cellpose(gpu=self.gpu, model_type=self.type)

    def detect_objects(self, diameter):
        # evalute the model on the image
        self.output = self.model.eval([image], channels=[0, 0], diameter=diameter)
        list_of_labels = self.output[0]
        self.image_label = list_of_labels[0]

    def get_label(self):
        return self.image_label    


class AnisotropyFrameLabel:
    def __init__(self, image):
        self.model_type = "anisotropy"
        self.image = image
        self.label = self.generate_label(image)

    def get_result(self):
        return SegmentedImage(self.image, self.label)    


    def generate_label(self, image):
        x, y = image.shape
        midpoint = int(x / 2)

        diff = 50  # workaround to get roughly aligned parallel channel

        label = np.zeros_like(image)

        label[:, :midpoint] = 2
        label[:, midpoint - diff:] = 1

        # perpendicular = image[:, :midpoint]
        # parallel = image[:, midpoint - diff:]

        return label
    