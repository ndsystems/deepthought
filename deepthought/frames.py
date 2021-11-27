# model describing data from the microscope
from labels import AnisotropyFrameLabel

class Frame:
    """basic unit of data from the microscope"""
    def __init__(self, image, coords):
        self.image = None
        self.coords = None



class AnisotropyFrame(Frame):
    def __init__(self, image, coords):
        super().__init__(image, coords)
        self.get_objects()

    def get_objects(self):
        self.segments = AnisotropyFrameLabel(image)
        self.objects = self.segments.get_regions()

        self.parallel = self.objects[0]
        self.perpendicular = self.objects[1]