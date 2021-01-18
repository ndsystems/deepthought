import tifffile
from cellpose import models

def using_gpu():
    # are we using GPU?
    use_GPU = models.use_gpu()
    print('>>> GPU activated? %d'%use_GPU)
    return use_GPU

def sim_image_data():
    img_3D = tifffile.imread("sim_data/DAPI.tif")
    images = img_3D[13, 512:1024, 512:1024]
    return images

def segment_nuclei(list_of_images):
    # segment the list of images with cellpose and return the labeled image
    model = models.Cellpose(gpu=1, model_type='nuclei')
    
    output = model.eval(list_of_images)
    
    list_of_masks = output[0]
    return list_of_masks

if __name__ == "__main__":
    list_of_images = [sim_image_data()]
    list_of_masks = segment_nuclei(list_of_images)
