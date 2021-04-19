"""
To do:

1. configure number of cameras and camera parameters easily from user code.
2. xy, z into a position object.
    Stage.x
    
"""
import numpy as np
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.plans import count, scan
from databroker import Broker

from devices import Camera, Focus

# other devices have to be added.
# to figure out where 


bec = BestEffortCallback()
bec.disable_plots()

db = Broker.named("temp")


RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)

class Microscope:
    def __init__(self, mmc):
        self.name = None
        self.mmc = mmc
        self._cam = [Camera(mmc)]
        self.z = Focus(mmc)
        self.xy = None

    def snap(self, num=1, delay=0):
        # run a blue sky count method with cameras
        # return uid
        uid, = RE(count(self._cam, num=num, delay=None))
        
        # https://nsls-ii.github.io/databroker/generated/databroker.Header.table.html#databroker.Header.table
        header =  db[uid]

        img = np.stack(header.table()["camera"].array)
        
        return img

