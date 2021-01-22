import napari

def imshow(image, label=None):
    with napari.gui_qt():
        viewer = napari.view_image(image, name="image at x,y")

        if label is not None:
            viewer.add_labels(label)
