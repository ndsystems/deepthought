from bluesky.plans import scan, count
from bluesky import RunEngine
from databroker import Broker
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.broker import LiveTiffExporter
from devices import Camera, Focus

from comms import client
from configs import config
from segmentation import segment_nuclei


import matplotlib.pyplot as plt

bec = BestEffortCallback()
bec.disable_plots()
db = Broker.named('temp')
template = "output_dir/{start[scan_id]}_{event[seq_num]}.tiff"
live = LiveTiffExporter("camera", template=template, db=db, overwrite=True)

RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)
RE.subscribe(live)
mmc = client(**config["mm_server"]).mmc

cam = Camera(mmc)
motor = Focus(mmc)
uid, = RE(count([cam], num=1))

header = db[uid]
print(header.table())

# list_of_masks = segment_nuclei(list_of_images)

# plt.imshow(list_of_masks[0])
# plt.imshow(list_of_images[1], cmap="gray")
# plt.show()


