from bluesky.plans import scan
from bluesky import RunEngine
from bluesky.utils import ProgressBarManager
from mm_bluesky import Focus, Camera
from comms import get_object

mmc = get_object(port=18861).mmc

RE = RunEngine({})
RE.waiting_hook = ProgressBarManager()

z = Focus(mmc)
cam = Camera(mmc)

from ophyd.sim import det
RE(scan([det], z, 0, 10, num=9))
