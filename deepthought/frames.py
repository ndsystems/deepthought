# model describing unit data from the microscope

from labels import Labeller, LabelledImage
from detection import AnisotropyFrameDetector, NuclearDetector
from utils import pad_images_similar
from compute import calculate_anisotropy
from transform import register
import numpy as np
from collections import OrderedDict
from view import view
from coords import rc_to_cart
import pandas as pd
from data import db
from process import clear_border


class DetectedObject:
    def __init__(self):
        self.vector = OrderedDict()
        self.raster = OrderedDict()


class ObjectsCollection:
    def __init__(self, channel, regions):
        self.channel = channel
        self.regions = regions
        self.detected_objects = []

        for region in self.regions:
            ob = self.region_to_object(region)
            self.detected_objects.append(ob)

        del self.regions

    def region_to_object(self, region):
        ob = DetectedObject()
        ob.raster[self.channel.marker] = region.intensity_image
        ob.vector["coords"] = region.xy
        return ob

    def merge_secondary(self, objs):
        for primary, secondary in zip(self.detected_objects, objs.detected_objects):
            primary.raster.update(secondary.raster)


class Frame:
    """basic unit of data from the microscope"""

    def __init__(self, image, coords, channel, pixel_size):
        self.image = image
        self.coords = coords
        self.channel = channel
        self.pixel_size = pixel_size

    def clean_up(self):
        del self.image

    def get_label(self):
        image = self.image
        detector = self.channel.detector
        frame_label = Labeller(image, detector).make()
        cleared = clear_border(frame_label)
        return cleared

    def get_objects(self, frame_label):
        regions = LabelledImage(self.image, frame_label).get_regions()
        regions = self.correct_frame_object_xy(regions, self.image)
        objects = ObjectsCollection(channel=self.channel, regions=regions)
        return objects

    def correct_frame_object_xy(self, regions, image):
        # coordinate transformation from rc to cartesian
        for reg in regions:
            rc_coords = np.array([reg.centroid])
            coords, _ = rc_to_cart(rc_coords, image=image)
            x, y = coords[0]
            x = x * self.pixel_size
            y = y * self.pixel_size
            x_microns = np.around(x + self.coords[0])
            y_microns = np.around(y + self.coords[1])
            reg.xy = [x_microns, y_microns]

        return regions


class FrameCollection:
    """collection of frames, that are to be processed together and has a primary label identifying
    objects of common interest.

    An example of a primary label is DAPI image for nuclei identification"""

    def __init__(self):
        self.collection = []

    def add_frame(self, frame):
        self.collection.append(frame)


class SingleLabelFrames(FrameCollection):
    def __init__(self):
        super().__init__()

    def get_objects(self):
        self.primary_label = self.collection[0].get_label()
        primary_objs = self.collection[0].get_objects(self.primary_label)

        for frame in self.collection[1:]:
            objs = frame.get_objects(frame_label=self.primary_label)
            primary_objs.merge_secondary(objs)

        self.objects = primary_objs
        return self.objects


class ObjectsAlbum:
    def __init__(self):
        self.objects_collection_group = OrderedDict()
        self.detected_objects = []
        self.count = 0

    def add_object_collection(self, uid, objects_collection):
        self.objects_collection_group[uid] = objects_collection
        self.count += len(objects_collection.detected_objects)
        self.detected_objects.extend(objects_collection.detected_objects)

    def __getitem__(self, value):
        return self.detected_objects[value]

    def get_data_from_uid(self, uid):
        table = db[uid].table()
        data = np.stack(table["image"].to_numpy())
        return data

    def view_raw(self, value):
        uid = list(self.objects_collection_group.items())[value][0]
        img = self.get_data_from_uid(uid)
        view(img)

    def get_coords(self):
        coords = []

        for uid, objects_collection in self.objects_group.items():
            coords.extend(
                [
                    detected_obj.vector["coords"]
                    for detected_obj in objects_collection.detected_objects
                ]
            )

        return coords


class AnisotropyFrame(Frame):
    """basic unit of anisotropy imaging frame"""

    def __init__(self, image, coords, model=None):
        if model is None:
            model = AnisotropyFrameDetector()

        super().__init__(image, coords, model)
        self.get_objects()

    def get_objects(self):
        # This currently does not currently get_objects
        self.label = Labeller(self.image, self.model)

        self.parallel = self.label.result.objects[0].intensity_image
        self.perpendicular = self.label.result.objects[1].intensity_image

        self.parallel, self.perpendicular = pad_images_similar(
            self.parallel, self.perpendicular
        )

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


class CellularFrame(Frame):
    def __init__(self, image, coords, channel):
        super().__init__(image, coords, channel)
