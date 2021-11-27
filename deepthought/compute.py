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


def calculate_anisotropy(parallel, perpendicular, g_factor=0.95, bg=100):
    """Subtract bg, and calculate anisotropy"""

    # bg is also subtracted from regions outside the nucleus, which makes it
    # -100, resulting in incorrect anisotropy
    parallel = parallel - bg
    perpendicular = perpendicular - bg

    amap = calculate_r(parallel, perpendicular, g_factor)
    return amap


def calculate_r(parallel, perpendicular, g_factor):
    """
    Parameters
    ----------
    parallel : ndarray
        Parallel channel

    perpendicular : ndarray
        Perpendicular channel

    g_factor : float
        Correction factor to remove bias in detection

    Returns
    -------
    anisotropy_map : ndarray
        Anisotropy image
    """
    numerator = (parallel - (g_factor * perpendicular))
    denominator = (parallel + (2 * g_factor * perpendicular))

    with np.errstate(divide='ignore', invalid='ignore'):
        anisotropy_map = np.true_divide(numerator, denominator)
        anisotropy_map[~ np.isfinite(anisotropy_map)] = 0

    anisotropy_map[anisotropy_map >= 1] = 0
    anisotropy_map[anisotropy_map <= 0] = 0

    return anisotropy_map


