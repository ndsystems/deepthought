"""
microscope abstraction layer
--
handles all the abstractions of human API with the microscope.


construction
--
a microscope is made up of modular device components that work together
to orchestrate an experimental task. 

these modules are   
    1. XYStage
        1. xy position
        2. limits of stage
    2. NosePiece
        1. Objectives
        2. Z value
    3. EnteringLight
        1. LightSources
            1. LED
                1. Intensity
                2. Wavelength
            2. Hallide
                1. Intensity
        2. Shutters 
        3. Optics
            1. Mirrors
            2. Condensor
    4. ExitingLight
        1. ViewPorts
            1. Detectors
                1. exposure
                2. gain
                3. binning
            2. EyePiece


usage primitives
--
The microscope is fundamentally used by a user to make visual/abstract observations of the
 samples thru one or more ViewPorts. 

The user configures the devices appropriately according to their wishes of
how the light should enter or exit the sample.

For example:
    if I want to image DAPI image, EnteringLight is configured such that
        1. LED is on, set to 405, with an intensity determined by a feedback
            system.

This abstraction allows us to group devices according to their functionality,
and create a more of an end-image centric organization of the device
primitives to define common microscopy tasks, which is what this section aims to encode.

user API
--

What a user does with their microscope, is their own business, but there are patterns
in usage that can be utilized to form an abstraction that can be used to generalize use
cases so as to code it into a system. Such abstractions are ideal design parameters for
APIs.

We intend to map the user API with the System, in order to figure out the microscope 
abstraction



Notes
--
1. One can in-principle keep exposure constant and vary intensity of light source
2. 50-50 can be a ViewPort of the Detector kind, where there is an
    exposure_factor of 2.                        

"""

from devices import Camera, Focus
# other devices have to be added.
# to figure out where 

from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.plans import count, scan
from databroker import Broker

bec = BestEffortCallback()
bec.disable_plots()

db = Broker.named("temp")


RE = RunEngine({})
RE.subscribe(bec)
RE.subscribe(db.insert)

class Microscope:
    def __init__(self, mmc):
        self.name = None
        self.mmc = mmc
        self._cam = [Camera(mmc)]
        self.z = Focus(mmc)
        self.xy = None

    def snap(self, num=1, delay=0):
        # run a blue sky count method with cameras
        # return uid
        uid, = RE(count(self._cam, num=num, delay=None))
        header =  db[uid]
        return header

