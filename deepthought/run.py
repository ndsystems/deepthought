from bluesky.plans import scan, count
from bluesky import RunEngine
from databroker import Broker
from bluesky.callbacks.best_effort import BestEffortCallback
from devices import Camera, Focus, SimMMC
from comms import client
from configs import config
from detection import detect_object
from viz import imshow


bec = BestEffortCallback()
bec.disable_plots()

db = Broker.named('temp')

# mmc = client(**config["mm_server"]).mmc
mmc = SimMMC()

cam = Camera(mmc)
motor = Focus(mmc)

RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)
RE(count([cam], num=1))


# to access the data, get the header object (of databroker)
# and access the data of camera
header = db[-1]

data = header.data("camera")
img = next(data)
(_, label) = detect_object(img)
stage_coords = [1242, -1012]

imshow(img, label, stage_coords)