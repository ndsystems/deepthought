import tifffile
from cellpose import models

def using_gpu():
    # are we using GPU?
    use_GPU = models.use_gpu()
    print('>>> GPU activated? %d'%use_GPU)
    return use_GPU

def image_data():
    img_3D = tifffile.imread("sim_data/DAPI.tif")
    images = img_3D[11:15, 512:1024, 512:1024]
    return images


# DEFINE CELLPOSE MODEL
# model_type='cyto' or model_type='nuclei'
model = models.Cellpose(gpu=using_gpu(), model_type='nuclei')

# diameter of the nucleus
diameter_of_nucleus = 150


images = image_data()

images = [images[2]]

params = model.eval(images, diameter=diameter_of_nucleus)
tifffile.imsave("masks.tiff", params[0])
