from bluesky.plans import scan, count
from bluesky import RunEngine
from databroker import Broker
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.broker import LiveTiffExporter
from devices import Camera, Focus, SimMMC
from comms import client
from configs import config
from segmentation import segment_nuclei
from viz import imshow

bec = BestEffortCallback()
bec.disable_plots()

db = Broker.named('temp')
live = LiveTiffExporter("camera", 
                        template="test_dir/{start[scan_id]}_{event[seq_num]}.tiff", 
                        db=db,
                        overwrite=True)

# mmc = client(**config["mm_server"]).mmc
mmc = SimMMC()

cam = Camera(mmc)
motor = Focus(mmc)

RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)
RE.subscribe(live)

uid, = RE(count([cam], num=1))
# header = db[uid]
# print(header.table())
