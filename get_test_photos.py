#!/bin/env python3

import cv2
from pprint import *
from picamera2 import Picamera2, Preview
import time

def main():
    picam = Picamera2()
    config = picam.create_video_configuration({'size': (640, 480), 'format': 'RGB888'})
    picam.configure(config)
    picam.start()

    while True:
        fname = input("Enter filename: ")
        if fname == "":
            break
        array = picam.capture_array()
        cv2.imwrite(fname + ".png", array)


if __name__ == "__main__":
    main()