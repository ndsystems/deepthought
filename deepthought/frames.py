# model describing unit data from the microscope

from labels import Labeller
from detection import AnisotropyFrameDetector
from utils import pad_images_similar
from compute import calculate_anisotropy
from transform import register
import napari
from collections import OrderedDict
from view import AlbumViewer
import pandas as pd


class Frame:
    """basic unit of data from the microscope"""

    def __init__(self, image, coords, model):
        self.image = image
        self.coords = coords
        self.model = model
        self.t = 0


class Album:
    def __init__(self):
        self.current_group = "frames"
        # data[0] = []
        # data[1] = []
        # data[2] = []
        #
        self.data = OrderedDict()

    def get_data(self):
        keys = self.album.data.keys()

        time_data = []

        for key in keys:
            data = self.frame_set_to_df(self.album.data[key])
            time_data.append(data)

        return pd.concat(time_data)

    def frame_set_to_df(self, frame_set):
        list_of_frame_data = []
        for frame in frame_set:
            list_of_frame_data.append(frame.read())

        return pd.DataFrame(list_of_frame_data)

    def add_frame(self, frame, group_name=None):
        if group_name is None:
            group_name = self.current_group

        if group_name not in self.data:
            self.initiate_group(group_name)

        self._add_frame(frame, group_name)

    def _add_frame(self, frame, group_name):
        self.data[group_name].append(frame)

    def initiate_group(self, name):
        self.data[name] = []

    def set_current_group(self, name):
        self.current_group = name

    def view(self):
        viewer = AlbumViewer(self)
        viewer.view()


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
        v.add_image(self.amap, colormap="jet", contrast_limits=[0.01, 0.28])

    def read(self):
        values = [self.parallel, self.amap]
        keys = ["image", "anisotropy"]

        data = OrderedDict()

        for key, value in zip(keys, values):
            data[key] = value

        return data
