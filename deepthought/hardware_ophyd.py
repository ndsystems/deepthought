from bluesky.plans import scan
from bluesky import RunEngine
from databroker import Broker
from mm_bluesky import Focus, Camera
from comms import get_object

RE = RunEngine({})
db = Broker.named('temp')
RE.subscribe(db.insert)

mmc = get_object(addr="localhost", port=18861).mmc
z = Focus(mmc)
cam = Camera(mmc)

uid, = RE(scan([cam], z, 0, 10, num=9))

header = db[uid]
print(header.table())
