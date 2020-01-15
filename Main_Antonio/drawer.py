import cv2 as cv
import numpy as np
import random as rng
from utils.utilities import extract_information
from PIL import  Image

###################################### INNER FUNCTIONS ######################################

def __check_masses(contours, min_area, min_perimeter, max_area, max_perimeter):
    '''
    The function checks if the masses (contours) present in the image are in a specified range
    in terms of area and perimeter. If not they are discarded.
    :param contours: the masses present in a mammogram image.
    :return: the list of all the masses that satisfy the check conditions.
    '''
    new_contours = []
    if len(contours) < 1:
        return new_contours
    else:
        for i in range(len(contours)):
            check_perimeter = cv.arcLength(contours[i], True) > min_perimeter and cv.arcLength(contours[i], True) < max_perimeter
            check_area = cv.contourArea(contours[i]) > min_area and cv.contourArea(contours[i]) < max_area
            if check_area and check_perimeter:
                new_contours.append(contours[i])
        return new_contours

def __set_threshold(threshold_image, thr_value):
    '''
    The function compute the threshold of a mammogram image (the output of the CNN) in order to
    distinguish masses from not relevant details in the breast.
    :param threshold_image: the image on which the threshold is applied.
    :param thr_value: the empyrical threshold value.
    :return: the list of all the masses.
    '''
    ret,thr_img = cv.threshold(threshold_image,thr_value,255,0,cv.THRESH_BINARY+cv.THRESH_OTSU)
  
    # Remove fat borders of the breast
    kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
    thr_img = cv.morphologyEx(thr_img, cv.MORPH_OPEN, kernel)

    # Masses
    _, contours, _ = cv.findContours(thr_img, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    return contours

def __saving_results(outcomes, ground_truths, paths):
    print("-------------------- [STATUS] Saving results -------------------------")
    for out, ground, path in zip(outcomes, ground_truths, paths):
        pil_1 = Image.fromarray(out)
        pil_2 = Image.fromarray(ground)
        pil_1.save("dataset/results/outcomes/" + path)
        pil_2.save("dataset/results/groundtruth/" + path)

#############################################################################################

def my_draw_contours(segmeted_images, ground_path, paths):
    '''
    The function extract the masses on the current mammogram image and draw them on the original
    image.
    :param segmeted_images: the list of images to be segmented.
    :return: a tuple of list containing the segmented images and the relative groundtruths.
    '''
    min_area, average_area, max_area, min_perimeter, average_perimeter, max_perimeter = extract_information(ground_path)
    print(min_area)
    print(average_area)
    print(max_area)
    print(min_perimeter)
    print(average_perimeter)
    print(max_perimeter)

    print("-------------------- [STATUS] Drawing contours -----------------------")
    ground_images = []
    outcomes = []
    for img in segmeted_images:
        # Threshold: 122 is an empirical value
        contours = __set_threshold(img, 122)
        # Checks value below 122. Threshold: 105 is another empirical value.
        contours = __check_masses(contours, min_area, min_perimeter, max_area+2000, max_perimeter+200)

        if len(contours) == 0:
            contours = __set_threshold(img, 105)
            contours = __check_masses(contours, min_area, min_perimeter, max_area+2000, max_perimeter+200)

        drawing = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
        for i in range(len(contours)):
            color = (rng.randint(0,256), rng.randint(0,256), rng.randint(0,256))
            # Draw groundtruth
            cv.drawContours(img, contours, i, color, 2)
            # Draw masses on img
            cv.drawContours(drawing, contours, i, (255, 255, 255), -1)  # -1 = FILLED
        
        cv.imshow("Identify", img)
        cv.imshow("Extrapolation", drawing)
        cv.waitKey()
        outcomes.append(img)
        ground_images.append(drawing)
    print("-------------------- [NOTIFY] All images have been processed ---------")
    __saving_results(outcomes, ground_images, paths)
    return  outcomes, ground_images

def clean_unet_images(input_unet_images, output_unet_images):
    '''
    The function cleans the output images of the U-Net by removing background and artefacts
    using as masks the original input images.
    :param input_unet_images: the list of images used as maks (512x512).
    :param output_unet_images: the list of images to be cleaned.
    :return: the list of cleaned images.
    '''
    print("-------------------- [STATUS] Processing U-Net output ----------------")
    segmeted_images = []
    for mask, out in zip(input_unet_images, output_unet_images):
        # Force pixel into range [0; 255]
       # print("MASCHERA :",mask)
        
        mask=cv.resize(mask,(512,512))
        
        mask = mask*255
        mask = mask.astype('uint8')
        # Erosion for removing U-Net noise
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (8, 8))
        mask = cv.erode(mask, kernel, iterations=3)
        # Creating the mask to clean the image
        ret, mask = cv.threshold(mask, 1, 255, 0, cv.THRESH_BINARY + cv.THRESH_OTSU)
        # Force pixel into range [0; 255]
        
        out=cv.resize(out,(512,512))
        
        #out = out * 255
        #out = out.astype('uint8')
        # Cleaning
        out[mask == 0] = 0

        segmeted_images.append(out)
    print("-------------------- [NOTIFY] Outputs processed ----------------------")
    return segmeted_images
