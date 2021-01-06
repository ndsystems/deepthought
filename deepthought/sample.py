"""Abstract representation of a Sample used in imaging."""
from collection import OrderedDict


class Form:
    """A physical object onto which the sample resides.
    
    The sample is a polygon with a defined shape that mark the boundaries
    within which Objects reside. This can be an array of stage coordinates.

    The orientation of the Sample Form can also be unique.
    """
    def __init__(self):
        # what function best describes the polygon shape of the Sample
        self.shape = None
        
        # how is the sample oriented
        self.orientation = None


class Sample:
    """A sample is an entity with physical form within which
    biological entities occupy space.

    There are often conditions of the sample that are common to all
    entities within the sample. These establish the sample identity.
    """
    def __init__(self, name):
        # give me a name
        self.name = name

        # material properties of the sample
        self.form = Form()

        # who or what am I?
        self.identity = SampleIdentity()


class SampleIdentity:
    """What identities do Samples have. 
    
    Is it dead or alive?
    What are the flurophores present in the sample?
    Does it look like the plate from last week that didn't work?
    Does it have any contamination?
    Is it going thru apoptosis? 
    """
    def __init__(self, sample):
        # Am I a Sample of a Sample?
        self.parent = None

        # what are the taxanomical specifics of the sample
        # example -> "HeLa"
        self.taxa = None
        
        # is the sample fixed or alive -> boolean
        self.living = None
        
        # under what condition does the sample exist
        # example -> control or treatment with MMS (0.01%) from start_time
        self.conditions = None

        # what are the flourescent dyes present in the sample?
        self.dyes = None
        

class Object:
    """Objects is an individual biological entity that exist within the form
    of a Sample.

    Objects will have to be identified in a Sample, either manually or
    using an algorithm.
   """
    def __init__(self):
        # who and what am i?
        self.identity = ObjectIdentity()


class ObjectIdentity:
    """What is the identity of the sample."""
    def __init__(self):
        # where did I come from
        self.parent = None
        
        # where is the object in xy
        self.xy = None
        
        # what are the variable parameters to image the sample in
        self.imaging_matrix = ImagingMatrix()


class ImagingMatrix:
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


class SampleMap:
    """Picture of where and how things are."""
    pass
