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


def axial_length(num_px, mag, binning, det_px_size):
    unit_pixel_in_micron = (det_px_size /
                            mag) * binning

    total_axial_length = unit_pixel_in_micron * num_px

    return total_axial_length
