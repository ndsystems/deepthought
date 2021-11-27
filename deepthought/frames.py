# model describing unit data from the microscope

from labels import Labeller
from detection import AnisotropyFrameDetector
from utils import pad_images_similar
from compute import calculate_anisotropy
from transform import register
import napari


class Frame:
    """basic unit of data from the microscope"""
    def __init__(self, image, coords, model):
        self.image = image
        self.coords = coords
        self.model = model


class Album:
    def __init__(self):
        self.frames = list()

    def add_frame(self, frame):
        self.frames.append(frame)


class AlbumObjects:
    def __init__(self, album):
        self.album = album
        self.objects = list()

    def objects_from_album(self):
        for frame in self.album:
            self.objects.append(frame.label.result.objects)


class AnisotropyFrame(Frame):
    """basic unit of anisotropy imaging frame"""
    def __init__(self, image, coords, model=None):
        if model is None:
            model = AnisotropyFrameDetector()

        super().__init__(image, coords, model)
        self.get_objects()

    def get_objects(self):
        self.label = Labeller(self.image, self.model)

        self.parallel = self.label.result.objects[0].intensity_image
        self.perpendicular = self.label.result.objects[1].intensity_image

        self.parallel, self.perpendicular = pad_images_similar(self.parallel,
                                                self.perpendicular)

        self.perpendicular = register(self.parallel, self.perpendicular)

        self.amap = calculate_anisotropy(self.parallel, self.perpendicular)

    def view(self):
        v = napari.Viewer()
        layer = v.add_image(self.parallel)
        v.add_image(self.amap, colormap="jet")
