"""abstractions for object viewer in object dashboard"""
from collection import OrderedDict


class Form:
    """A physical object onto which the sample resides.
    
    This can be a rectangular entity, circular entity or an array entity.
    
    The form can have geometrical information of the sample
    which enables computations of factors like sample tilt, or
    displacement upon perturbance, and adjust it in one place.


    Note
    ----
    # talk to an architect to design this better.
    """
    def __init__(self):
        self.shape = None
        self.size = None


class Sample:
    """A sample is a multi-dimensional physical entity.
    
    It is materially constructed with certain design goals, onto forms
    such as dishes or slide, each optimizing for parameters such as cost,
    performance, sample consideration.
    
    With in these forms, collections of biological entity occupy space.
    Each sample object can therefore be identified with a xy coordinate.
    """
    def __init__(self, name):
        # give me a name
        self.name = name

        # who or what am I?
        self.identity = SampleIdentity()

        # are there objects associated with me?
        self.objects = None

        # material properties of the sample
        self.form = Form()

        # is there a map of myself?
        self.map = SampleMap()


class SampleIdentity:
    """What is the identity of the sample which is common across objects.
    
        * is the sample dead or alive.
        * is it is a cell or a tissue.
        * what is the type of the sample.
        * what are the conditions of the sample.
        * what are the channels in the sample.
    """
    def __init__(self, sample):
        # boolean
        self.living = None
        # at what biological level is the sample
        self.level = None
        # what type of sample is it
        self.sample_type = None
        # under what condition does the sample exist
        self.conditions = None
        # what are the channels in the sample
        self.channels = None


class Object:
    """Lower level entity in the sample that points to a point in space
    denoting a biological entity.

    This could be an individual cell (xy) or a region in tissue (xyz).
    """
    
    def __init__(self):
        # who and what am i?
        self.identity = None

        # where do I look for my history?
        self.history = None    

    def identify(self):
        pass


class ObjectIdentity:
    """What is the identity of the sample.
    
        * where is the object in xy.
        * what are the channels present.
        * what is the imaging matrix for the object.
    """
    def __init__(self, obj):
        # where did I come from
        obj.parent = None
        # where is the object in xy
        obj.xy = None
        # which sample channels are present in the object
        obj.channels = None
        # how does one best image this object.
        obj.imaging_matrix = ImagingMatrix()


class ImagingMatrix():
    """Information on how to image any object in the sample. This could
    be the relavant exposure time, binning, gain, camera choice, and any
    other customizations associated with the image."""
    def __init__(self):
        self.exposure = None
        self.gain = None
