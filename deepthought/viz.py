import napari
import numpy as np
from skimage import measure


def make_bbox(bbox_extents):
    minr = bbox_extents[0]
    minc = bbox_extents[1]
    maxr = bbox_extents[2]
    maxc = bbox_extents[3]

    bbox_rect = np.array([[minr, minc], [maxr, minc], [maxr, maxc],
                          [minr, maxc]])
    bbox_rect = np.moveaxis(bbox_rect, 2, 0)

    return bbox_rect


def circularity(perimeter, area):
    """Calculate the circularity of the region

    Parameters
    ----------
    perimeter : float
        the perimeter of the region
    area : float
        the area of the region

    Returns
    -------
    circularity : float
        The circularity of the region as defined by 4*pi*area / perimeter^2
    """
    circularity = 4 * np.pi * area / (perimeter**2)

    return circularity


def transform_xy(x, y, stage_coords):
    # currently this does not really transform the coordinate system

    stage_coords = np.array(stage_coords)

    x = np.around(x + stage_coords[0])
    y = np.around(y + stage_coords[1])

    return list(zip(x, y))

def imshow(image, label_image=None, *args, **kwargs):
    with napari.gui_qt():
        viewer = napari.view_image(image, name="image")

        if label_image is not None:
            print("here")
            viewer.add_labels(label_image, visible=False, name="segments")


def imshow_sp(image, label_image, stage_coords):
    with napari.gui_qt():
        viewer = napari.view_image(image, name="DAPI")

        viewer.add_labels(label_image, visible=False, name="segments")

        # create the properties dictionary
        properties = measure.regionprops_table(label_image,
                                               properties=("label", "bbox",
                                                           "perimeter", "area",
                                                           "centroid"))
        properties["circularity"] = circularity(properties["perimeter"],
                                                properties["area"])
        properties["xy"] = transform_xy(properties["centroid-0"],
                                        properties["centroid-1"], stage_coords)
        # create the bounding box rectangles
        bbox_rects = make_bbox([properties[f"bbox-{i}"] for i in range(4)])

        # specify the display parameters for the text
        text_parameters = {
            "text": "label: {label}\nxy: {xy}\ncirc: {circularity:.2f}",
            "size": 12,
            "color": "green",
            "anchor": "upper_left",
            "translation": [-3, 0],
        }

        shapes_layer = viewer.add_shapes(bbox_rects,
                                         face_color="transparent",
                                         edge_color="green",
                                         properties=properties,
                                         text=text_parameters,
                                         name="properties",
                                         visible=False)
