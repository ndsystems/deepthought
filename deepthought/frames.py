# model describing unit data from the microscope

from labels import Labeller
from detection import AnisotropyFrameDetector

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
    def __init__(self, frames):
        self.frames = frames
        self.objects = list()

    def objects_from_frames(self):
        for frame in self.frames:
            self.objects.append(frame.label.result.regions)


class AnisotropyFrame(Frame):
    """basic unit of anisotropy imaging frame"""
    def __init__(self, image, coords, model=None):
        if model is None:
            model = AnisotropyFrameDetector()

        super().__init__(image, coords, model)
        self.get_objects()

    def get_objects(self):
        self.label = Labeller(image, model)
        self.label.generate_label()


        self.parallel = self.label.result.regions[0]
        self.perpendicular = self.label.result.regions[1]


