import sys
import traceback
from microscope import Microscope
from detection import detect_object
from viz import imshow

# https://valelab4.ucsf.edu/~MM/doc/MMCore/html/class_c_m_m_core.html


# bs - bright star microscope
bs = Microscope()

imgs = bs.scan()

bs.mmc.setCameraDevice("right_port")

# images = bs.snap(num=1)
# labels=detect_object(images)
# imshow(images)
