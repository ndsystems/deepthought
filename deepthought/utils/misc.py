import numpy as np


def pad_images_similar(img1, img2):
    list_of_images = [img1, img2]

    padded_list = []
    a = 0
    b = 0

    for image in list_of_images:
        x, y = image.shape
        if x > a:
            a = x
        if y > b:
            b = y

    for image in list_of_images:
        nuc_a, nuc_b = image.shape
        if b > a:
            limit_a = int(round(b / 2)) - int(round(nuc_a / 2))
            limit_b = int(round((b - nuc_b) / 2))
            padded = np.zeros([b, b])
            padded[limit_a : nuc_a + limit_a, limit_b : nuc_b + limit_b] = image
        else:
            limit_a = int(round((a - nuc_a) / 2))
            limit_b = int(round(a / 2)) - int(round(nuc_b / 2))
            padded = np.zeros([a, a])
            padded[limit_a : nuc_a + limit_a, limit_b : nuc_b + limit_b] = image

        padded_list.append(padded)
    return padded_list
