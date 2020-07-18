from hardware_handler import Acqusition
import itertools
import numpy as np


class ImageSeries:
    def __init__(self):
        self.tasks = []
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
    
    def z_scan(self, positions):
        self._z_task = lambda: (self.z(pos) for pos in positions)
        self.tasks.append(self._z_task)

    def exp_scan(self, exposures):
        self._exp_task = lambda: (self.exp(e) for e in exposures)
        self.tasks.append(self._exp_task)

    def run(self, n):
        for generator in self.tasks[n]():
            next(generator)
            m=n+1
            if m < len(self.tasks):
                self.run(m)

    def __image(self):
        print("imaging")
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
    s.run(0)