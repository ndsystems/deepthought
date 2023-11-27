from cellpose import models
import numpy as np


class Detector:
    def __init__(self, name, type_):
        self.name = name
        self.type_ = type_


class NuclearDetector(Detector):
    def __init__(self):
        super().__init__(name="cellpose", type_="nuclei")
        self.gpu = 1
        self.diameter = 100  # use unit conversion here
        self.create_model()

    def create_model(self):
        # define a cellpose model
        self.model = models.Cellpose(gpu=self.gpu, model_type=self.type_)

    def detect(self, image):
        # evalute the model on the image
        output = self.model.eval([image], channels=[0, 0], diameter=self.diameter)
        list_of_labels = output[0]
        label = list_of_labels[0]
        return label


class AnisotropyFrameDetector(Detector):
    def __init__(self):
        super().__init__(name="anisotropy", type_="frame")

    def detect(self, image):
        x, y = image.shape
        midpoint = int(x / 2)

        diff = 50  # workaround to get roughly aligned parallel channel

        label = np.zeros_like(image)

        label[:midpoint, :] = 1
        label[midpoint - diff :, :] = 2

        return label
