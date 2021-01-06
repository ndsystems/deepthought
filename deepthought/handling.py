from sample import Form, Sample


class SampleBuilder:
    def __init__(self):
        # for dapi stained HeLa plate
        self.plate = Form("36mm_dish")
        self.sample = Sample("HeLa")
        self.sample.identity.channels = ["BF", "DAPI"]
    
    def build(self):
        # where is the object in XYStage space of the Sample?
        # since objects are unique in space, 
        #   1. segmenting the raw DAPI image
        #   2. label objects and compute regionprops
        #   3. calculate stage coordinates for image coordinates
        pass

