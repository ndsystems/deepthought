import napari
import pandas as pd
import numpy as np


class AlbumViewer:
    def __init__(self, album):
        self.album = album

    def view(self):
        data = self.album.get_data()

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
