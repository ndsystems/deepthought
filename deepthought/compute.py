import numpy as np


def circularity(perimeter, area):
    """Calculate the circularity of the region

    Parameters
    ----------
    perimeter : float
        the perimeter of the region
    area : float
        the area of the region

    Returns
    -------
    circularity : float
        The circularity of the region as defined by 4*pi*area / perimeter^2
    """
    circularity = 4 * np.pi * area / (perimeter**2)

    return circularity


def unit_pixel_length():
    magnification_objective_lens = 100
    image_binning = 8  # 1, 2, 4, 8
    detector_pixel_size = 6.5  # um

    unit_pixel_in_micron = (detector_pixel_size /
                            magnification_objective_lens) * image_binning

    return unit_pixel_in_micron


def axial_length():
    number_of_axial_pixels = 512

    total_axial_length = unit_pixel_length() * number_of_axial_pixels

    return total_axial_length
