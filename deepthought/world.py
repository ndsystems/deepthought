# has the functions to build the world of the sample space

class Layers:
    pass

def calculate_axial_length():
    magnification_objective_lens = 100
    image_binning = 1 # 1, 2, 4
    detector_pixel_size = 6.5 # um
    number_of_pixels = 2048

    unit_pixel_in_micron = (detector_pixel_size / magnification_objective_lens) * image_binning
    total_axial_length = unit_pixel_in_micron * number_of_pixels

    return total_axial_length


def stage_grids():
    x_range = [-50000, 50000]
    y_range = [-50000, 50000]

    smallest_step_size = 0.1


def raster_space():
    pass

def vector_space():
    pass

def space_referencing():
    pass
    
