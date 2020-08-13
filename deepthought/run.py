from bluesky.plans import scan, count
from bluesky import RunEngine
from databroker import Broker
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.broker import LiveTiffExporter
from mm_bluesky import Camera

bec = BestEffortCallback()
bec.disable_plots()
db = Broker.named('temp')
template = "output_dir/{start[scan_id]}_{event[seq_num]}.tiff"
live = LiveTiffExporter("camera", template=template, db=db)

RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)
RE.subscribe(live)

cam = Camera()


uid, = RE(count([cam], num=10, delay=1))

header = db[uid]
print(header.table())