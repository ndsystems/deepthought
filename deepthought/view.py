import napari
import pandas
import numpy as np

class AlbumViewer:
    def __init__(self, album):
        self.album = album

    def get_data(self):
        list_of_frame_data = []
        for frame in self.album.frames:
            list_of_frame_data.append(frame.read())

        return pandas.DataFrame(list_of_frame_data)

    def view(self):
        data = self.get_data()
        imgs = np.stack(data["image"].to_numpy())
        v = napari.Viewer()
        v.add_image(imgs, name="image")
        # viewer.add_image(np.stack(data["anisotropy"].to_numpy()), 
        #                     name="anisotropy", colormap="jet", 
        #                     contrast_limits=[0.03, 0.25])
        v.show()