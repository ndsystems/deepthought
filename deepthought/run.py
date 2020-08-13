from bluesky.plans import scan, count
from bluesky import RunEngine
from databroker import Broker
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.broker import LiveTiffExporter
from mm_bluesky import Camera, Focus

from comms import client
from configs import config


bec = BestEffortCallback()
bec.disable_plots()
db = Broker.named('temp')
template = "output_dir/{start[scan_id]}_{event[seq_num]}.tiff"
live = LiveTiffExporter("camera", template=template, db=db, overwrite=True)

RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)
RE.subscribe(live)

mmc = client(**config["mm_server"]).load_microscope()
cam = Camera(mmc)
motor = Focus(mmc)

uid, = RE(scan([cam], motor, 0, 10, 10))

header = db[uid]
print(header.table())