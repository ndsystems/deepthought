from hardware_handler import Acqusition
import itertools
import numpy as np



class SingleScan:
    # returns a generator object
    def __init__(self, list_):
        self.list_ = list_
        self.gen = self.create_generator()

    def create_generator(self):
        yield from self.list_

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.gen)
           

class RecursiveScan(SingleScan):
    def __iter__(self):
        return self
        
    def __next__(self):
        try:
            return next(self.gen)
        except StopIteration:
            self.gen = self.create_generator()
            raise StopIteration()



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

    def run(self):
        for generator_0 in self.tasks[0]():
            next(generator_0)
            for generator_1 in self.tasks[1]():
                next(generator_1)
                for generator_2 in self.tasks[2]():
                    next(generator_2)

    def __repr__(self):
        return str(self.self.tasks)


if __name__ == "__main__":
    s = ImageSeries()
    positions = [[0, 0], [100, 100], [1000, 1000]]
    s.xy_scan(positions)
    s.exp_scan([50, 100, 150])
    s.z_scan([0, 100, 1000, 10000])
    s.run()