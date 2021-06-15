from skimage.draw import disk
import numpy as np
from data import db
import napari
from detection import segment, find_object_properties, calculate_stage_coordinates
import matplotlib.pyplot as plt
from bluesky_live.run_builder import RunBuilder
from compute import axial_length, circularity
from matplotlib.widgets import RadioButtons
import pandas as pd


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

    def __init__(self, image=None, coords=None, timestamp=None, label=None):
        self.image = image
        self.coords = coords
        self.timestamp = timestamp
        self.label = label
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

        for properties in self._entities:
            entity = Entity(properties, self.coords)
            self.entities.append(entity)

    def __repr__(self):
        return f"{self.coords, self.timestamp, len(self.entities)}"


class Entity:
    """A cell or a tissue, which has been identified from an image of
    it, using computer vision"""

    def __init__(self, properties, stage_coords):
        self.properties = properties
        self.stage_coords = stage_coords
        self.calculate_properties()

        self._data = {"x": self.x,
                      "y": self.y,
                      "intensity": self.intensity,
                      "area": self.area,
                      "circ": self.circ}

        self.data = pd.Series(data=self._data)
        # self.id = unique()

    def img_to_stage(self):
        x, y = self.properties.centroid

        # stage offset
        self.x = x + self.stage_coords[0]
        self.y = y + self.stage_coords[1]

        self.xy = [self.x, self.y]

    def calculate_properties(self):
        self.img_to_stage()
        self.intensity = np.mean(self.properties.intensity_image)
        self.area = self.properties.area
        self.circ = circularity(self.properties.perimeter, self.area)


class Disk:
    def __init__(self, center):
        self.center = center
        self.diameter = 13 * 1000  # mm - > um

        self.rr, self.cc = disk(self.center, self.diameter/2)
        self.coords = [self.rr, self.cc]
        self.num = 3  # int(self.diameter / axial_length())


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
        self.header = db[self.uid]

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


class SelectFromCollection:
    """
    Select indices from a matplotlib collection using `LassoSelector`.

    Selected indices are saved in the `ind` attribute. This tool fades out the
    points that are not part of the selection (i.e., reduces their alpha
    values). If your collection has alpha < 1, this tool will permanently
    alter the alpha values.

    Note that this tool selects collection objects based on their *origins*
    (i.e., `offsets`).

    Parameters
    ----------
    ax : `~matplotlib.axes.Axes`
        Axes to interact with.
    collection : `matplotlib.collections.Collection` subclass
        Collection you want to select from.
    alpha_other : 0 <= float <= 1
        To highlight a selection, this tool sets all selected points to an
        alpha value of 1 and non-selected points to *alpha_other*.
    """

    def __init__(self, ax, collection, alpha_other=0.3):
        self.canvas = ax.figure.canvas
        self.collection = collection
        self.alpha_other = alpha_other

        self.xys = collection.get_offsets()
        self.Npts = len(self.xys)

        # Ensure that we have separate colors for each object
        self.fc = collection.get_facecolors()
        if len(self.fc) == 0:
            raise ValueError('Collection must have a facecolor')
        elif len(self.fc) == 1:
            self.fc = np.tile(self.fc, (self.Npts, 1))

        self.lasso = LassoSelector(ax, onselect=self.onselect)
        self.ind = []

    def onselect(self, verts):
        path = Path(verts)
        self.ind = np.nonzero(path.contains_points(self.xys))[0]
        self.fc[:, -1] = self.alpha_other
        self.fc[self.ind, -1] = 1
        self.collection.set_facecolors(self.fc)
        self.canvas.draw_idle()

    def disconnect(self):
        self.lasso.disconnect_events()
        self.fc[:, -1] = 1
        self.collection.set_facecolors(self.fc)
        self.canvas.draw_idle()


class SampleVisualizer:
    def __init__(self, image_uid=None, process_uid=None, image_header=None, process_header=None):

        self.image_uid = image_uid
        self.process_uid = process_uid

        self.image_header = image_header
        self.process_header = process_header

        if self.image_uid is not None:
            self.image_header = db[self.image_uid]

        if self.process_uid is not None:
            self.process_header = db[self.process_uid]

        self.image_table = self.image_header.table()
        self.process_table = self.process_header.table("process")

        self._entities = []
        self.fov_xy = []
        self.fovs = []

        for (_, image_row), (_, process_row) in zip(self.image_table.iterrows(), self.process_table.iterrows()):
            coords = [image_row["xy_stage_x"],
                      image_row["xy_stage_y"], image_row["z"]]
            image = image_row["camera"]
            label = process_row["label"]

            f = FoV(image=image, coords=coords, label=label)
            self.fovs.append(f)

            f.make_entities()
            self._entities.extend([_.data for _ in f.entities])
            self.fov_xy.append(coords[:2])

        self.entities = pd.DataFrame(data=self._entities)

    def plot(self):

        fig, ax = plt.subplots(1)
        ax.scatter(self.entities.x, self.entities.y, s=1, picker=True)
        ax.set(xlabel="x", ylabel="y")

        axcolor = 'lightgoldenrodyellow'
        ray = plt.axes([0.05, 0.7, 0.15, 0.15], facecolor=axcolor)
        rax = plt.axes([0.7, 0.05, 0.15, 0.15], facecolor=axcolor)

        self.x_option = "x"
        self.y_option = "y"

        radio_x = RadioButtons(
            rax, self.entities.columns.values, active=0)

        radio_y = RadioButtons(
            ray, self.entities.columns.values, active=1)

        def x_selector(label):
            self.x_option = label
            replot()

        def y_selector(label):
            self.y_option = label
            replot()

        def replot():
            ax.clear()
            ax.scatter(self.entities[self.x_option],
                       self.entities[self.y_option], s=1, picker=True)
            ax.set_xlabel(self.x_option)
            ax.set_ylabel(self.y_option)
            plt.draw()

        radio_x.on_clicked(x_selector)
        radio_y.on_clicked(y_selector)

        # center = [-31706.9, -833.0]
        # circle = plt.Circle(center, radius=13000/2, fill=False)

        # ax.set_aspect(1)
        # ax.add_patch(circle)

        # # f_x, f_y = zip(*self.fov_xy)
        # # ax.scatter(f_x, f_y, s=1, c="r", picker=True)

        # def onpick(evn):
        #     self.fovs[evn.ind[0]].show()

        # fig.canvas.mpl_connect('pick_event', onpick)
        plt.show()


if __name__ == '__main__':
    # currently, it is single tp, fixed cells
    # we need:
    # live cell timetraces for objects
    #   * s-phase biology with HT pcna-cb

    dapi = Channel("DAPI")
    dapi.exposure = 30
    dapi.model = "nuclei"

    tritc = Channel("TRITC")
    tritc.exposure = 100

    center = [-31706.9, -833.0]

    do_image = False
    if do_image:
        from microscope import Microscope
        scope = Microscope()

        timepoints = []
        for t in range(100):
            s = SampleConstructor(scope,
                                  form=Disk(center=center),
                                  channels=[dapi, tritc])
            s.map()
            timepoints.append(s)
            print(t, len(s._map))

    access_test = False
    if access_test:
        for i in range(1, 62, 2):

            s = SampleVisualizer(image_header=db[-i - 1],
                                 process_header=db[-i])
            s.plot()
