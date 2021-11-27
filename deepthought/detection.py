from cellpose import models

class NuclearDetector:
    def __init__(self):
        self.name = "cellpose"
        self.type = "nuclei"
        self.gpu = 1
        self.diameter = 100 # use unit conversion here
        self.create_model()
        
    def create_model(self):
        # define a cellpose model
        self.model = models.Cellpose(gpu=self.gpu, model_type=self.type)

    def detect(self, image):
        # evalute the model on the image
        output = self.model.eval([image], channels=[0, 0], diameter=diameter)
        list_of_labels = output[0]
        label = list_of_labels[0]
        return label

class AnisotropyFrameDetector:
    def __init__(self):
        self.name = "anisotropy"
        self.type = "frame"
    
    def detect(self, image):
        x, y = image.shape
        midpoint = int(x / 2)

        diff = 50  # workaround to get roughly aligned parallel channel

        label = np.zeros_like(image)

        label[:, :midpoint] = 2
        label[:, midpoint - diff:] = 1

        return label
