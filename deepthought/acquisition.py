from hardware_handler import Acqusition
import numpy as np


class Scan():
    """This uses the idea of yielding to perform tasks sequentially, when sequences of
    hardware tasks would have to be performed by the user before acquiring each image.


    Example use case: for each position in xy, and for a defined z region, check focus,
    adjust exposure, and take an image in a list of channels.
    
    asyncio tasks might be a better way of doing this than yield statements
    """

    # stores a list of generators that will be run in sequence till each task is complete.

    task = []

    def __init__(self):
        pass

    def z_scan(self, *args):
        self.task.append(self.__z_scan(*args))

    def __z_scan(self, start, stop, step):
        z_list =  np.arange(start, stop+step, step)
        for z in z_list:
            print("moving to z :", z)
            yield self.__z(z)

    def __z(self, z):
        yield z #self.z = pos
    
    def xy_scan(self, *args):
        self.task.append(self.__xy_scan(*args))

    def __xy_scan(self, xy_list):
        for xy in xy_list:
            print("moving to xy :", xy)
            yield self.__xy(xy)    

    def __xy(self, xy):
        yield xy #self.xy = xy

    def run(self):
        # does not work as required
        print("Running")
        while True:
            if len(self.task) == 0:
                break

            for count, _ in enumerate(self.task):
                try:
                    print(count)
                    next(_)
                except StopIteration:
                    self.task.remove(_)

        print("Finished Run")

if __name__ == "__main__":
    s = Scan()
    xy_list = [(100, 100), (1,1)]
    s.xy_scan(xy_list)
    s.z_scan(0, 100, 10)
    # s.image()
    # s.run()