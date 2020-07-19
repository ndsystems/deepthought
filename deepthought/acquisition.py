from hardware_handler import Scope, BaseImaging, Illumination
import numpy as np

class Acqusition(Scope, BaseImaging):
    pass


class ImageSeries:
    """To orchestrate an image series by calling methods sequentially.
    
    These methods can invoke different higher order tasks, such as scanning a
    list of xy points, or establishing the optimal exposure, focus.

    The output of the image series is a numpy array with dimensions as defined
    by the sequence of calling the methods. 
    
    """

    def __init__(self):
        self.tasks = [] # list of task method calls
        self.images = [] # images are appended to this -> np.array
        self.shapes = [] # keeps track of the shape of individual tasks
        self.scope = Acqusition() # gives access to hardware functionality

    def xy(self, xy_position):
        """A generator that moves the stage to a XY position"""
        print(f"xy: {xy_position}")
        self.scope.xy = xy_position 
        yield

    def z(self, z_position):
        """A generator that moves the stage to a Z position"""
        print(f"z: {z_position}")
        self.scope.z = z_position 
        yield

    def exp(self, exposure_time):
        """A generator that sets current exposure time"""
        print(f"exp: {exposure_time}")
        self.scope.exposure = exposure_time
        yield

    def _image(self):
        """A generator that captures an image with current settings"""
        print("imaging")
        image = self.scope.image()
        self.images.append(image)
        yield 

    def generic_scan(self, scan_fn, list_of_values):
        """Call a scan function on a list of values"""
        self._scan_task = lambda: (scan_fn(value) for value in list_of_values)
        self.tasks.append(self._scan_task)
        self.shapes.append(len(list_of_values))
    
    def xy_scan(self, xy_position_list):
        """Scan a list of positions in XY dimension"""
        self.generic_scan(self.xy, xy_position_list)

    def z_scan(self, z_position_list):
        """Scan a list of positions in Z dimension"""
        self.generic_scan(self.z, z_position_list)

    def exp_scan(self, exposure_time_list):
        """Scan a list of exposures"""
        self.generic_scan(self.exp, exposure_time_list)

    def image(self):
        """Take an image"""
        self.image_ = lambda: (self._image() for _ in [None])
        self.tasks.append(self.image_)

    def run_tasks(self, n):
        """Run recursively a list of tasks, which are generator expressions,
        generating individual generators
        
        This is an equivalent of nested for-loops.
        """
        for generator in self.tasks[n]():
            next(generator)
            m=n+1
            if m < len(self.tasks):
                self.run_tasks(m)

    def run(self):
        """
        1. Runs the tasks
        2. Repacks the images into a numpy array
        3. Reshapes the array into the same dimensions as that of the tasks.
        """
        self.run_tasks(0)
        self.images = np.array(self.images)
        self.shapes.extend(self.images.shape[-2:])

        self.images = np.reshape(self.images, self.shapes)

    def __repr__(self):
        return str(self.tasks)


if __name__ == "__main__":
    s = ImageSeries()
    positions = [[0, 0], [100, 100], [1000, 1000]]
    s.xy_scan(positions)
    s.z_scan([0, 100, 1000, 1500])
    s.exp_scan([50, 100, 150])
    s.image()
    # s.run()