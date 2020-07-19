from hardware_handler import Acqusition
import numpy as np


class ImageSeries:
    def __init__(self):
        self.tasks = []
        self.images = []
        self.shapes = []
        #self.scope = Acqusition()

    def xy(self, position):
        print(f"xy: {position}")
        yield #self.scope.xy = position 

    def z(self, position):
        print(f"z: {position}")
        yield #self.scope.z = position 

    def exp(self, exposure):
        print(f"exp: {exposure}")
        yield #self.scope.exposure = exposure

    def xy_scan(self, positions):
        self._xy_task = lambda: (self.xy(pos) for pos in positions)
        self.tasks.append(self._xy_task)
        self.shapes.append(len(positions))
    
    def z_scan(self, positions):
        self._z_task = lambda: (self.z(pos) for pos in positions)
        self.tasks.append(self._z_task)
        self.shapes.append(len(positions))

    def exp_scan(self, exposures):
        self._exp_task = lambda: (self.exp(e) for e in exposures)
        self.tasks.append(self._exp_task)
        self.shapes.append(len(exposures))

    def _run(self, n):
        for generator in self.tasks[n]():
            next(generator)
            m=n+1
            if m < len(self.tasks):
                self._run(m)
                print(m)

    def run(self):
        self._run(0)
        self.images = np.array(self.images).reshape(self.shapes)

    def __image(self):
        print("imaging")
        self.images.append(1)
        yield

    def image(self):
        self._image = lambda: (self.__image() for _ in [None])
        self.tasks.append(self._image)
    
    def __repr__(self):
        return str(self.tasks)


if __name__ == "__main__":
    s = ImageSeries()
    positions = [[0, 0], [100, 100], [1000, 1000]]
    s.xy_scan(positions)
    s.z_scan([0, 100, 1000, 10000])
    s.exp_scan([50, 100, 150])
    s.image()
    s.run()