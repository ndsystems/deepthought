import scipy.ndimage as ndi
from skimage import filters, segmentation, morphology, measure


def otsu(image):
    """Calculate Otsu's threshold for a given image.

    Parameters
    ----------
    image : (N, M) array
        Image for which the threshold has to be calculated.

    Returns
    -------
    threshold : float
        Otsu's threshold value
    """
    threshold = filters.threshold_otsu(image)
    return threshold


def median(image, **kwds):
    """Apply a median filter to the image.

    Parameters
    ----------
    image : (N, M) array
        Input image

    Returns
    -------
    image : (N, M) array
        Median filtered image
    """
    return ndi.median_filter(image, **kwds)


def gaussian(image, **kwds):
    """Apply a gaussian filter to the image.

    Parameters
    ----------
    image : (N, M) array
        Input image

    Returns
    -------
    image : (N, M) array
        Gaussian filtered image
    """
    return ndi.filters.gaussian_filter(image, **kwds)


def remove_small(image, min_size=5, **kwds):
    """Remove small objects.

    Parameters
    ----------
    image : (N, M) bool array
        Binary input image.

    min_size : int
        Objects with size less than this will be removed.

    Returns
    -------
    image : (N, M) bool array
        Binary image
    """
    return morphology.remove_small_objects(image, min_size, **kwds)


def clear_border(labelled_image, **kwds):
    """Clear objects that are touching the image boundary.

    Parameters
    ----------
    image : (N, M) array
        label image

    Returns
    -------
    image : (N, M) bool array
        relabelled image.
    """
    binary = labelled_image > 0
    cleared = segmentation.clear_border(binary, **kwds)
    relabelled = label(binary)
    return relabelled


def fill_holes(image, **kwds):
    """Fill the holes in connected objects in a binary image.

    Parameters
    ----------
    image : (N, M) bool array
        Binary image where objects with holes have to be filled.

    Returns
    -------
    image : (N, M) bool array
        Binary image with filled holes in the connected objects.

    """
    return ndi.binary_fill_holes(image, **kwds)


def label(binary_image):
    _label = measure.label(binary_image)
    return _label
