import napari
import pandas as pd
import numpy as np


class AlbumViewer:
    def __init__(self, album):
        self.album = album

    def get_data(self):
        dims = self.album.data.keys()

        time_data = []

        for dim in dims:
            data = self.frame_set_to_df(self.album.data[dim])
            time_data.append(data)

        return pd.concat(time_data)

    def frame_set_to_df(self, frame_set):
        list_of_frame_data = []
        for frame in frame_set:
            list_of_frame_data.append(frame.read())

        return pd.DataFrame(list_of_frame_data)

    def view(self):
        data = self.get_data()

        imgs = np.stack(data["image"].to_numpy())
        amaps = np.stack(data["anisotropy"].to_numpy())

        dims = len(self.album.data.keys())
        imgs = imgs.reshape(dims, -1, *imgs.shape[-2:])
        amaps = amaps.reshape(dims, -1, *imgs.shape[-2:])

        v = napari.Viewer()
        v.add_image(imgs, name="image")
        v.add_image(amaps,
                    name="anisotropy", colormap="jet",
                    contrast_limits=[0.03, 0.25])
        v.show()
