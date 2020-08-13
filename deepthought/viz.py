import napari

def imshow(image):
    with napari.gui_qt():
        self.viewer = napari.Viewer()
        self.viewer.add_image(image)
