import numpy as np
import SimpleITK as sitk


def estimate(img1, img2):
    """Estimate the transformation matrix for img2, with respect to fixed img1.

    Parameters
    ----------
    img1 : (N, M) numpy array
        Fixed image

    img2 : (N, M) numpy array
        Misaligned image

    Returns
    -------
    Transformation Parameter Map : SuperElastix transformation parameters
    """
    elastix = sitk.ElastixImageFilter()
    elastix.LogToConsoleOff()
    elastix.SetParameterMap(sitk.GetDefaultParameterMap("affine"))

    elastix.SetFixedImage(sitk.GetImageFromArray(img1))
    elastix.SetMovingImage(sitk.GetImageFromArray(img2))

    elastix.Execute()
    return elastix.GetTransformParameterMap()


def align(estimation, img2):
    """Align the given image with the given transformation parameter map.

    Parameters
    ----------
    estimation : GetTransformParameterMap() object from SuperElastix
        The estimated transformation map returned by `estimate()`.

    img2 : (N, M) numpy array
        Image to be aligned

    Returns
    -------
    aligned image : (N, M) numpy array
        The aligned image.
    """
    transformix = sitk.TransformixImageFilter()
    transformix.LogToConsoleOff()
    transformix.SetTransformParameterMap(estimation)
    transformix.SetMovingImage(sitk.GetImageFromArray(img2))
    transformix.Execute()

    return sitk.GetArrayFromImage(transformix.GetResultImage())


def register(img1, img2):
    estimation = estimate(img1, img2)
    aligned = align(estimation, img2).astype(np.int16)

    return aligned
