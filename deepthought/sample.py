from skimage.draw import disk
import numpy as np
from microscope import Microscope
from data import db
import napari
from detection import segment, find_object_properties, calculate_stage_coordinates


class FoV:
    """FoV or Field of View is the most basic unit of data in a microscope.

    A field is defined as an area of observation from the microscope.

    Any field will have

    * image
        the data acquired by the detector

    * stage coordinates
        to locate the field in the coordinate space of the stage

    * timestamp
        indicating when the field was observed

    * kind
        keyword that describes what is the data in the image
        this information can be used by deepthought to choose
        appropriate models for visual processing"""

    def __init__(self, image=None, coords=None, timestamp=None):
        self.image = image
        self.coords = coords
        self.timestamp = timestamp

    def show(self):
        napari.view_image(self.image)

    def __repr__(self):
        return f"{self.coords, self.timestamp}"


class SampleScan:
    """Constructs an initial Sample entity.

    To construct a sample,
        1. take uid from bluesky and convert to FoVs
        2. identify Enti)ty(s) from FoV
        3. append entities to Sample
    """

    def __init__(self):
        self.scope = Microscope()

    def generate_fov(self):
        # generate FoVs of sample

        uid = self.scope.snap(channel="BF")

        self.header = db[uid]

        df = self.header.table()

        for _, row in df.iterrows():
            time = row["time"]
            image = row["camera"]
            coords = [row["xy_stage_x"], row["xy_stage_y"], row["z"]]
            FoV(image=image, coords=coords,
                timestamp=time, kind="cyto")


class Disk:
    def __init__(self, center):
        self.center = center
        self.diameter = 13 * 1000  # mm - > um
        self.rr, self.cc = disk(self.center, self.diameter/2)
        self.coords = [self.rr, self.cc]


class Channel:
    def __init__(self, name="BF"):
        self.name = name
        self.exposure = None
        self.model = None

        if self.exposure is None:
            self.auto_exposure()

    def auto_exposure(self):
        self.exposure = 100


class SampleConstructor:
    def __init__(self, form=None, channels=None):
        self.form = form
        self.channels = channels

    def map(self, *args, **kwargs):
        self._map = []

        pass


if __name__ == '__main__':
    dapi = Channel("DAPI")
    dapi.exposure = 30
    dapi.model = "nuclei"

    scope = Microscope()
    center = scope.mmc.getXYPosition()

    control = SampleConstructor(
        form=Disk(center=center),
        channels=[dapi])

    control.map(n=100)
