#!/bin/env python3

import time

stime = time.time()
import cv2
print(f"Time to load cv2: {time.time() - stime}")
stime = time.time()
from picamera2 import Picamera2
print(f"Time to load picamera2: {time.time() - stime}")

from pprint import *
import argparse

# Read 640x480 frames as fast as possible

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("outdir")
    args = parser.parse_args()

    picam = Picamera2()
    sensor_modes = sorted(picam.sensor_modes, key=lambda x: x['size'][0])    
    # find the sensor mode that's at least 640x480
    for sm in sensor_modes:
        if sm['size'][0] >= 640:
            mode = sm
            break
    else:
        print("no modes for 640x? found.")
        exit(1)

    print(f"Using sensor mode: {mode}")    
    config = picam.create_video_configuration({'size': (640, 480)}, raw=mode)
    picam.configure(config)
    picam.start()
    photos = {}
    start = time.time()
    for i in range(args.count):
        photos[time.time()] = picam.capture_array()
    picam.stop()
    picam.close()
    elapsed = time.time() - start
    print(f"Reading {args.count} photos took {elapsed}, {elapsed/args.count} per photo")

    for p in photos:
        cv2.imwrite(args.outdir + "/" + str(p) + ".png", photos[p])



if __name__ == "__main__":
    main()