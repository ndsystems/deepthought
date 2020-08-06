import matplotlib
matplotlib.use('qt5agg')
from bluesky.plans import scan
from bluesky import RunEngine
from bluesky.utils import ProgressBarManager
from mm_bluesky import Focus, Camera
from comms import get_object
from databroker import Broker

mmc = get_object(addr="localhost", port=18861).mmc

RE = RunEngine({})

RE.waiting_hook = ProgressBarManager()
db = Broker.named('temp')

RE.subscribe(db.insert)

z = Focus(mmc)
cam = Camera(mmc)

import ophyd
# z = ophyd.sim.motor
# cam = ophyd.sim.direct_img

uid, = RE(scan([cam], z, 0, 10, num=9))
header = db[uid]

