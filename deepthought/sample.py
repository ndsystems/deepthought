"""abstractions for object viewer in object dashboard"""
from collection import OrderedDict


class Form:
    """A physical object onto which the sample resides.
    
    This can be a rectangular entity, circular entity or an array entity.
    
    Note
    ----
    # talk to an architect to represent this better.
    """
    def __init__(self):
        self.shape = None
        self.size = None

class Sample:
    """A sample is a multi-dimensional physical entity.
    
    It is materially constructed with certain design goals, onto forms
    such as dishes or slide, each optimizing for parameters such as cost,
    performance, sample consideration.
    
    Within these forms, collections of biological entity occupy space.
    Each sample object can therefore be identified with a xy coordinate.
    """
    def __init__(self):
        # who or what am I?
        self.identity = None

        # a collection of SampleObjects
        self.objects = None

        # material properties of the sample
        # the form can have geometrical information of the sample
        # which enables computations of factors like sample tilt, or
        # displacement upon perturbance.
        self.form = None
    

class SampleIdentity:
    """What is the identity of the sample.
    
        * is the sample dead or alive.
        * is it is a cell or a tissue.
        * what is the type of the sample.
        * what are the conditions of the sample.
    """
    def __init__(self):
        # boolean
        self.living = None
        # at what biological level is the sample
        self.level = None
        # what type of sample is it
        self.sample_type = None
        # under what condition does the sample exist
        self.conditions = None


class SampleObject:
    """An object that represents an entity in the sample."""
    
    def __init__(self, xy):
        # who created me?
        self.parent = None 

        # where do I look for my history?
        self.history = None
        
        # where is the object in xy space of the Sample?
        # since objects are unique in space, 
        #   1. segmenting the raw DAPI image
        #   2. label objects and compute regionprops
        #   3. calculate stage coordinates for image coordinates
        self.xy = xy

        # how do I image the object?
        self.imaging_parameters = OrderedDict()        
