from comms import client
from devices import SimMMC
from microscope import Microscope
from detection import detect_object
from viz import imshow

# https://valelab4.ucsf.edu/~MM/doc/MMCore/html/class_c_m_m_core.html
# mmc = client(addr="10.10.1.62", port=18861).mmc
mmc = SimMMC()

# bs - bright star microscope
bs = Microscope(mmc)
images = bs.snap(num=4)
labels = detect_object(images)
imshow(images, labels)
