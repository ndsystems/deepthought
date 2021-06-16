from microscope import Microscope
from sample import FoV
from viz import imshow

# to do
# 1. object map
#   get objects, stage coords for individual images, add offset to them
#   check FoV
# 2. map a rectangle with corners defined
#   use the corner to define a grid for imaging

corners = {
    1: [-36292, -3397],
    2: [-27397, -3909],
    3: [-27028, 1683],
    4: [-36292, 1683]
}


# bs - bright star microscope
bs = Microscope()

uid = bs.snap(num=1)
