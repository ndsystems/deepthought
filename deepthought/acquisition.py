import asyncio
from comms import get_object
from hardware_handler import Scope, BaseImaging, Illumination
import numpy as np


class Acqusition(Scope, BaseImaging):
    pass


class Tasking:
    task_tree = [] # list of task method calls

    def run_tasks(self, task_index=0):
        """Run recursively a list of tasks, which are generator expressions,
        generating individual generators
        
        This is an equivalent of nested for-loops.
        """
        for generator in self.task_tree[task_index]():
            next(generator)
            # self.device_control.wait_for_device()
            
            next_index = task_index + 1
            if next_index < len(self.task_tree):
                self.run_tasks(next_index)



class Sequential(Tasking):
    """To orchestrate an image series by calling methods sequentially.
    
    These methods can invoke different higher order tasks, such as scanning a
    list of xy points, or establishing the optimal exposure, focus.

    The output of the image series is a numpy array with dimensions as defined
    by the sequence of calling the methods. 
    
    """

    images = [] # images are appended to this -> np.array
    shapes = [] # keeps track of the shape of individual task tree
    device_control = Acqusition() # gives access to hardware functionality

    def xy(self, xy_position):
        """A generator that moves the stage to a XY position"""
        print(f"xy: {xy_position}")
        self.device_control.xy = xy_position
        yield

    def z(self, z_position):
        """A generator that moves the stage to a Z position"""
        print(f"z: {z_position}")
        self.device_control.z = z_position 
        yield

    def exp(self, exposure_time):
        """A generator that sets current exposure time"""
        print(f"exp: {exposure_time}")
        self.device_control.exposure = exposure_time
        yield

    def _image(self):
        """A generator that captures an image with current settings"""
        print("imaging")
        self.images.append(self.device_control.image())
        yield

    def generic_scan(self, scanning_function, scan_values):
        """Call a scan function on a list of values"""
        self._scan_task = lambda: (scanning_function(value) for value in scan_values)
        self.task_tree.append(self._scan_task)
        self.shapes.append(len(scan_values))
    
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
        self.task_tree.append(self.image_)


    def run(self):
        """
        1. Runs the tasks
        2. Repacks the images into a numpy array
        3. Reshapes the array into the same dimensions as that of the tasks.
        """
        self.run_tasks()
        self.images = np.array(self.images)
        self.shapes.extend(self.images.shape[-2:])

        self.images = np.reshape(self.images, self.shapes)

    def __repr__(self):
        return str(self.task_tree)


if __name__ == "__main__":
    s = Sequential()
    positions = [[0, 0], [100, 100], [1000, 1000]]
    s.xy_scan(positions)
    s.exp_scan([50, 100])
    s.z_scan([0, 100])
    s.image()
