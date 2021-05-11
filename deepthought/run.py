from microscope import Microscope
from detection import detect_object
from viz import imshow


# bs - bright star microscope
bs = Microscope()
bs.mmc.setCameraDevice("right_port")

imgs = bs.snap()


labels = detect_object(imgs)
imshow(imgs, labels)
