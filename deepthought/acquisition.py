from hardware_handler import Acqusition
import numpy as np


class Scan(Acqusition):
    def __init__(self):
        pass

    def z_scan(self, start, stop, step):
        images = []

        scan_points = np.arange(start, stop + step, step)

        for pos in scan_points:
            self.z = pos
            images.append(self.image())

        return np.array(images)


if __name__ == "__main__":
    s = Scan()
    s.z_scan(10, 15, 1)
