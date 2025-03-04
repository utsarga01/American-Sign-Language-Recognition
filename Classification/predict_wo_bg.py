import os
import math
import numpy as np
import tensorflow as tf
import pickle
import cv2
from HandTrackingModule import HandDetector
from tensorflow.keras.preprocessing import image


def backgroundSubtraction(img):
    hsvim = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 48, 80], dtype="uint8")
    upper = np.array([20, 255, 255], dtype="uint8")
    skinMask = cv2.inRange(hsvim, lower, upper)
    # Blur the mask to help remove noise
    skinMask = cv2.blur(skinMask, (2, 2))
    # Get threshold image
    _, thresh = cv2.threshold(skinMask, 100, 255, cv2.THRESH_BINARY)

    # Find the hand contour
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    hand_contour = max(contours, key=lambda x: cv2.contourArea(x))
    # Create a black background
    black_bg = np.zeros_like(img)

    # Draw the hand contour on the black image
    cv2.drawContours(black_bg, [hand_contour], -1, (255, 255, 255), thickness=cv2.FILLED)

    # Apply the mask to the original frame
    hand_pixels = cv2.bitwise_and(img, black_bg)

    return hand_pixels


offset = 30
img_size = 128

model = tf.keras.models.load_model('cnn_model.h5')
cap = cv2.VideoCapture(0)
detector = HandDetector(maxHands=1)

with open('categories.pkl') as file:
    categories = eval(file.read())

while True:
    key = cv2.waitKey(10) & 0xFF
    if key == 27:  # Press ESC to exit
        break

    success, img = cap.read()
    hands, img = detector.findHands(img)
    img = cv2.flip(img, 1)

    if hands:

        # img = backgroundSubtraction(img)

        hand = hands[0]
        x, y, w, h = hand['bbox']
        imgCrop = img[y - offset : y + h + offset, -x - w + offset - 75 : -x + offset]

        aspect_ratio = h / w

        try:
            if aspect_ratio > 1:
                k = img_size / h
                wCal = math.ceil(k * w)
                imgResize = cv2.resize(imgCrop, (wCal, img_size))
                wGap = math.ceil((img_size - wCal) / 2)
                imgWhite = np.zeros((img_size, img_size, 3), np.uint8) * 255
                imgWhite[:, wGap : wCal + wGap] = imgResize
            else:
                k = img_size / w
                hCal = math.ceil(k * h)
                imgResize = cv2.resize(imgCrop, (img_size, hCal))
                hGap = math.ceil((img_size - hCal) / 2)
                imgWhite = np.zeros((img_size, img_size, 3), np.uint8) * 255
                imgWhite[hGap : hCal + hGap, :] = imgResize

        except Exception as e:
            pass

        imgWhite = cv2.flip(imgWhite, 1)
        imgWhite = backgroundSubtraction(imgWhite)
        my_image_arr = image.img_to_array(imgWhite)
        my_image_pixel = np.expand_dims(my_image_arr, axis=0)
        my_image_pixel /= 255

        prediction = model.predict(my_image_pixel, verbose=False)
        prediction_class = np.argmax(prediction, axis=1)
        c = categories[tuple(prediction_class)[0]]
        p = str(round(np.max(prediction), 2))

        cv2.putText(img, c, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (92, 13, 195), 3, cv2.LINE_AA)
        cv2.putText(img, p, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (92, 13, 195), 3, cv2.LINE_AA)

        cv2.imshow('', imgWhite)

    cv2.imshow('Image', img)

cv2.destroyAllWindows()
