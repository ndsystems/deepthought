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
    """What are the identities that define a sample."""
    def __init__(self, sample):
        # what are the taxanomical specifics of the sample
        # example -> "HeLa"
        self.taxa = None
        
        # is the sample fixed or alive -> boolean
        self.living = None
        
        # under what condition does the sample exist
        # example -> control or treatment with MMS (0.01%) from start_time
        self.conditions = None

        # how is the sample oriented in the Form geometry
        self.orientation = None
        

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
    """What is the identity of the sample."""
    def __init__(self):
        # where did I come from
        self.parent = None
        
        # where is the object in xy
        self.xy = None
        
        # what are the variable parameters to image the sample in
        self.imaging_matrix = ImagingMatrix()


class ImagingMatrix():
    """How to image any object in the sample."""
    def __init__(self):
        self.channels = None

    def update(self):
        self.light = Light(
            self.mode = None,
            self.intensity = None,
            )

        self.cam = Camera(
                self.exposure = None, 
                self.gain = None,
                self.bounding_box = None,
            )

        
