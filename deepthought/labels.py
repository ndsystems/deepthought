from skimage import measure
import numpy as np


class LabelledImage:
    # access all aspects of segmented image here.

    def __init__(self, image, label):
        self.image = image
        self.label = label

    def get_regions(self):
        # get individual label regions from image
        self.regions = measure.regionprops(self.label, intensity_image=self.image)
        return self.regions


class Labeller:
    def __init__(self, image, detector):
        self.image = image
        self.detector = detector

    def make(self):
        label = self.detector.detect(self.image)
        return label
