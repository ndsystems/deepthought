import napari
from comms import share_object
from configs import get_default

default = get_default()

viz_addr = default["server"]["viz"]

class Viewer:
    def __init__(self):
        pass

     
    def update_image(self, image):
        self.create(image)
        

    def create(self, image):
        with napari.gui_qt():
            self.viewer = napari.Viewer()
            self.viewer.add_image(image)

if __name__ == "__main__":
    v = Viewer()
    server = share_object(v, viz_addr) 
    server.run()
