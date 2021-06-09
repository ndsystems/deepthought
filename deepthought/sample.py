from skimage.draw import disk
import numpy as np
from microscope import Microscope
from data import db
import napari
from detection import segment, find_object_properties, calculate_stage_coordinates
import matplotlib.pyplot as plt
from bluesky_live.run_builder import RunBuilder
from compute import axial_length


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
        self.entities = []

    def show(self):
        v = napari.view_image(self.image, show=False)

        if self.label is not None:
            v.add_labels(self.label)

        v.show()

    def detect(self):
        self._detect()
        self.make_entities()

    def _detect(self):
        self.label = segment(self.image, "nuclei")

    def make_entities(self):
        self._entities = find_object_properties(self.label, self.image)

        for props in self._entities:
            entity = Entity(props, self.coords)
            self.entities.append(entity)

    def __repr__(self):
        return f"{self.coords, self.timestamp, len(self.entities)}"


class Entity:
    """A cell or a tissue, which has been identified from an image of
    it, using computer vision"""

    def __init__(self, props, stage_coords):
        self.props = props
        self.stage_coords = stage_coords
        self.img_to_stage()

    def img_to_stage(self):
        y, x = self.props.centroid

        # stage offset
        x = x + self.stage_coords[0]
        y = y + self.stage_coords[1]

        self.xy = [x, y]

    def aslist(self):
        return self.xy

    def __iter__(self):
        return iter(self.aslist())


class ExtendedEntity(Entity):
    pass


class Disk:
    def __init__(self, center):
        self.center = center
        self.diameter = 13 * 1000  # mm - > um
        self.rr, self.cc = disk(self.center, self.diameter/2)
        self.coords = [self.rr, self.cc]
        self.num = int(self.diameter / axial_length())


class Channel:
    def __init__(self, name="BF"):
        self.name = name
        self.exposure = None
        self.model = None

        if self.exposure is None:
            self.auto_exposure()

    def auto_exposure(self):
        self.exposure = 100

    def __repr__(self):
        return str(self.name)


class SampleConstructor:
    def __init__(self, scope=None, form=None, channels=None):
        self.scope = scope
        self.form = form
        self.channels = channels
        self.fovs = []
        self._map = []

        # temp
        # self.uid = "cc69f5ef-0904-434b-83ee-b78a85128cc2"

    def map(self, *args, **kwargs):
        if self.scope is not None:
            self.generate_fov()  # captures fov, creates self.uid
        self.access_data_header()  # creates self.header
        self.create_fov_from_table()  # creates self.fov
        self.process_fov()

    def generate_fov(self):
        # generate FoVs of sample
        channel = self.channels[0]  # temp fix, for testing

        self.uid = self.scope.scan(
            channel=channel.name, exposure=channel.exposure,
            center=self.form.center, num=self.form.num)

    def access_data_header(self):
        if hasattr(self, "uid"):
            self.header = db[self.uid]
        else:
            self.header = db[-1]

    @staticmethod
    def set_up_incremental_insert(run):
        db.insert("start", run.metadata["start"])
        run.events.new_doc.connect(db.insert)

    def process_fov(self):
        with RunBuilder(metadata={'detection': 'nuclei'}) as builder:
            builder.add_stream("process", data_keys={
                               "label": {"source": "segment", "dtype": "array", "shape": []}})
            run = builder.get_run()

            # self.set_up_incremental_insert(run)

            for fov in self.fovs:
                fov.detect()
                builder.add_data("process", data={'label': [fov.label]})
                self._map.extend(fov.entities)

            for name, doc in run.documents(fill="yes"):
                db.v1.insert(name, doc)

    def create_fov_from_table(self):
        table = self.header.table()

        for _, row in table.iterrows():
            time = row["time"]
            image = row["camera"]
            coords = [row["xy_stage_x"], row["xy_stage_y"], row["z"]]
            self.fovs.append(FoV(image=image, coords=coords,
                                 timestamp=time))

    def plot(self):
        xy = [e.xy for e in self._map]
        x, y = zip(*xy)
        plt.scatter(x, y, s=1)
        plt.show()


if __name__ == '__main__':
    dapi = Channel("DAPI")
    dapi.exposure = 30
    dapi.model = "nuclei"

    # currently, it is single tp, fixed cells
    # we need:
    # live cell timetraces for objects
    #   * s-phase biology with HT pcna-cb

    tritc = Channel("TRITC")
    tritc.exposure = 100

    center = [-31706.9, -833.0]

    scope = Microscope()
    control_1 = SampleConstructor(scope,
                                  form=Disk(center=center),
                                  channels=[dapi, tritc])

    control_1.map()

    # control_2 = SampleConstructor(scope)
