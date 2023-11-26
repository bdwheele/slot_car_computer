#!/bin/env python3

import cv2
from pprint import *
from picamera2 import Picamera2, Preview
import time
import argparse
import math

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('infile')
    parser.add_argument('outfile')
    args = parser.parse_args()
    stime = time.time()
    # read the image as grayscale
    src = cv2.imread(args.infile, cv2.IMREAD_GRAYSCALE)
    # do canny edge detection
    # args: src image, threshold1, threshold2, edges, aperturesize
    dst = cv2.Canny(src, 50, 200, None, 3)

    # get our destination image
    cdst = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)

    # get the lines
    lines = cv2.HoughLinesP(dst, 1, math.pi / 180, 50 , 10)
    if lines is not None:
        for i in range(len(lines)):
            l = lines[i][0]
            if(abs(l[0] - l[2]) < abs(l[1] - l[3])):
                color = (0, 255, 0)
            else:
                color = (0, 0, 255)
            cv2.line(cdst, (l[0], l[1]), (l[2], l[3]), color, 1, cv2.LINE_AA)
        cv2.imwrite(args.outfile, cdst)
    else:
        print("No lines found")

    print(f"Elapsed time: {time.time() - stime}")

if __name__ == "__main__":
    main()