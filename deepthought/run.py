from comms import client
from devices import SimMMC
from microscope import Microscope

# mmc = client(addr="10.10.1.62", port=18861).mmc
mmc = SimMMC()

bs = Microscope(mmc)
data_header = bs.snap(num=3)
df = data_header.table()
