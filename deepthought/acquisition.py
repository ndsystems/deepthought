from hardware_handler import Acqusition
import itertools
import numpy as np


class ImageSeries:
    def __init__(self):
        self.tasks = []

    def xy(self, position):
        print(f"xy: {position}")
        yield "xy"

    def z(self, position):
        print(f"z: {position}")
        yield "z"

    def exp(self, exposure):
        print(f"exp: {exposure}")
        yield "exposure"

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


    def __repr__(self):
        return str(self.self.tasks)


if __name__ == "__main__":
    s = ImageSeries()
    positions = [[0, 0], [100, 100], [1000, 1000]]
    s.z_scan([0, 100, 1000, 10000])
    s.xy_scan(positions)
    s.exp_scan([50, 100, 150])
    s.run(0)