#!/bin/env python3

#import cv2
from pprint import *
from picamera2 import Picamera2, Preview
import time

def main():
    picam = Picamera2()
    sensor_modes = sorted(picam.sensor_modes, key=lambda x: x['size'][0])    
    picam.close()           
    for s in ((1024, 768), (640, 480), (320, 240)):        
        for sm in sensor_modes: 
            if sm['size'][0] < s[0]:
                # requires upscaling
                continue
            for t in ('still', 'video', 'preview'):
                for f in ('XBGR8888', 'BGR888'):                
                    test(sm, t, s, f)
                    break
            break

    
    
    
def test(sensor_mode, conftype, size, format):
    smstring = f"{sensor_mode['size']} {sensor_mode['fps']}"
    picam = Picamera2()        
    if conftype == "still":
        config = picam.create_still_configuration({'size': size, 'format': format}, raw=sensor_mode)
    elif conftype == "video":
        config = picam.create_video_configuration({'size': size, 'format': format}, raw=sensor_mode)
    elif conftype == "preview":
        config = picam.create_preview_configuration({'size': size, 'format': format, }, raw=sensor_mode)
    picam.configure(config)
    picam.start()
    s = time.time()
    for i in range(0, 100):
        array = picam.capture_array()
    elapsed = time.time() - s
    print(f"{smstring:18s} {conftype:7s}  {str(size):11s}  {format:8s}  {elapsed/100:0.4f}")
    picam.stop()
    picam.close()



if __name__ == "__main__":
    main()