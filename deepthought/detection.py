import tifffile
from cellpose import models


def segment_nuclei(image):
    """Segment nuclei from image using cellpose and return the mask"""
    model = models.Cellpose(gpu=1, model_type='nuclei')
    
    output = model.eval([image])
    
    list_of_masks = output[0]
    return list_of_masks[0]


def detect_object(image, kind="dapi"):
    if kind == "dapi":
        seg_func = segment_nuclei
    
    label_ = seg_func(image)
    return (image, label_)
