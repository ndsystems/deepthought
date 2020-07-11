from hardware_handler import Acqusition
import numpy as np



class SingleScan:
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

class XYScan():
    def __init__(self, pos_list):
        self.pos_list = pos_list

    def __getitem__(self, index):
        print("moving stage position to ", next(self.pos_list))
    
    def __repr__(self):
        return "XY"


class ZScan():
    def __init__(self, pos_list):
        self.pos_list = pos_list

    def __getitem__(self, index):
        print("moving Z position to ", next(self.pos_list))
    
    def __repr__(self):
        return "Z"


class TScan():
    def __getitem__(self, index):
        # move things here
        print("Time point", next(self.time_list))

    def __repr__(self):
        return "T"

class MultiScan:
    tasks = []
    root = 1

    def xy_scan(self, list_):
        if self.root:
            scan_obj = XYScan(SingleScan(list_))
            self.root = 0
        else:
            scan_obj = XYScan(RecursiveScan(list_))

        self.tasks.append(scan_obj)

    def z_scan(self, list_):
        if self.root:
            scan_obj = ZScan(SingleScan(list_))
            self.root = 0
        else:
            scan_obj = ZScan(RecursiveScan(list_))

        self.tasks.append(scan_obj)

    def run(self):
        for _ in self.tasks[0]:
            for _ in self.tasks[1]:
                time.sleep(1)
    

if __name__ == "__main__":
    import time
    s = MultiScan()
    xy_list = [(100, 100), (1,1), (100, 1232)]
    s.z_scan([0, 100, 10])
    s.xy_scan(xy_list)
    