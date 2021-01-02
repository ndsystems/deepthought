"""abstractions for object viewer in object dashboard"""

class Sample:
    """A sample is a collection of objects, such as cells."""
    def __init__(self):
        # ideally a collection of SampleObjects, each with properties, such as
        # position [x, y, z], imaging parameters
        self.objects = None

        # transformation matrix that defines the orientation of the sample
        # objects to its own self. Useful to estimate orientation change
        # and update this variable.
        self.orientation = None


class SampleObject:
    def __init__(self, xy):
        self.xy = xy

    def getFoci():
        # get best z coordinate
        pass

    def getExposures():
        # get best exposure
        pass
    
    def getCameraParameters():
        # all parameters related to MMCore Camera object - ROI, binning, gain 
        pass

    def getImage():
        # image a range x,y,z coordinate
        pass


class TaskObjects:
    """Tasks that can be run on SampleObjects"""
    def update():
        pass
    
    def timelapse():
        pass

    def monitor():
        pass
