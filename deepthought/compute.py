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


def unit_pixel_length(mag, binning, det_px_size=6.5):
    mag = 60
    binning = 4

    unit_pixel_in_micron = (det_px_size /
                            mag) * binning

    return unit_pixel_in_micron


def axial_length(num_px, unit_px_length):

    total_axial_length = unit_px_length * num_px

    return total_axial_length
