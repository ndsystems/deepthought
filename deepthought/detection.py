import numpy as np
import tifffile
from cellpose import models


def segment_nuclei(image):
    """Segment nuclei from image using cellpose and return the mask"""
    model = models.Cellpose(gpu=1, model_type='nuclei', )
    
    output = model.eval([image])
    
    list_of_masks = output[0]
    return list_of_masks[0]

def segment_cyto(image):
    """Segment cell from image using cellpose and return the mask"""
    model = models.Cellpose(gpu=1, model_type='cyto', )
    
    output = model.eval([image])
    
    list_of_masks = output[0]
    return list_of_masks[0]

def detect_object(image, kind="dapi"):
    if kind == "dapi":
        seg_func = segment_nuclei
    
    elif kind == "cyto":
        seg_func = segment_cyto
    
    if image.shape[0] > 1:
        labels_ = np.array([seg_func(img) for img in image])
        
        return labels_

    label_ = seg_func(image)
    return label_
