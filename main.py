#!/usr/bin/env python3

import argparse
import http.server
import socketserver
import time
import threading
from enum import Enum
import logging
from picamera2 import Picamera2
from detect_lines import TrackGeometry, Line
import cv2
import sys
import statistics
import numpy as np

# global state that's shared with all threads...
class State(Enum):
    STARTUP = 1
    CALIBRATING = 2
    RUNNING = 3


current_state = State.STARTUP

# The lanes are calibrated
calibrated = False
# take a snapshot
snapshot = False
# shut everything down
shutdown = False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("--port", type=int, default=8000, help="Webserver port")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s: %(message)s")
    
    logging.info("Racetrack initialization started")
    threads = {'camera_thread': [None, camera_thread, []],
               'webserver_thread': [None, webserver_thread, [args.port]]}
    while not shutdown:
        for th, thdata in threads.items():
            if thdata[0] is None or not thdata[0].is_alive():
                logging.info(f"Starting thread {th}")
                thdata[0] = threading.Thread(target=thdata[1], args=thdata[2])
                thdata[0].start()
        time.sleep(5)


def camera_thread():
    global calibrated, snapshot, shutdown
    logging.info("Camera thread")
    picam = Picamera2()
    sensor_modes = sorted(picam.sensor_modes, key=lambda x: x['size'][0])    
    # find the sensor mode that's at least 640x480
    for sm in sensor_modes:
        if sm['size'][0] >= 640:
            mode = sm
            break
    else:
        logging.error("no camera modes for 640x? found.")
        exit(1)

    logging.info(f"Using sensor mode: {mode}")    
    config = picam.create_video_configuration({'size': (640, 480)}, raw=mode)
    picam.configure(config)
    #picam.set_controls({'ExposureTime': 100})
    picam.start()
    logging.info(f"Picam settings: {picam.controls}")
    geometry = None
    ltime = time.time()
    lfpts = [0]
    last_lap = [0, 0]
    while True:
        if not calibrated:
            logging.info("Starting calibration...")
            photo = picam.capture_array()
            #geometry = get_geometry(photo)
            geometry = TrackGeometry(photo)
            if geometry is None:
                logging.error("Cannot determine geometry, restarting calibration")
                continue
            
            #lfpts = get_finishpoints(photo, geometry)
            lfpts = geometry.read_lanes(photo)
            #logging.info(f"lfpts: {lfpts}")
            #decorate_with_geometry(photo, geometry)
            geometry.decorate_image(photo)
            cv2.imwrite(sys.path[0] + "/temp/calibration.png", cv2.cvtColor(photo, cv2.COLOR_BGR2RGB))

            

            logging.info("Calibration complete")
            calibrated = True

        now = time.time()
        photo = picam.capture_array()        
        fpts = geometry.read_lanes(photo)
        #logging.info(f"fpts: {fpts}")
        raw = np.subtract(lfpts, fpts)
        quant = np.right_shift(np.bitwise_and(raw, 0xf0), 4)
        means = [np.mean(x) for x in quant]
        #logging.info(quant)
        logging.info(f"Photo! {time.time() - ltime} ({means})")
        #for i, l in enumerate(quant):
        #    logging.info(f"Lane {i}: ({''.join(['0123456789ABCDEF'[x] for x in l])})")
        for i, m in enumerate(means):
            if m > 5 and time.time() - last_lap[i] > 10:
                logging.info(f"Lane {i} has crossed line, lap time: {now - last_lap[i]}")
                last_lap[i] = now
        
        
        if snapshot:
            cv2.imwrite(sys.path[0] + "/temp/snapshot.png", cv2.cvtColor(photo, cv2.COLOR_BGR2RGB))
            snapshot = False
        
        ltime = time.time()
        #lfpts = fpts


def webserver_thread(port):
    logging.info("Starting webserver thread")
    with socketserver.TCPServer(("", port), Webserver) as httpd:
        print("serving at port", port)
        httpd.serve_forever()


class Webserver(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        global calibrated, snapshot
        logging.info(f"Got GET request {self.path}: {self.headers}")
        if self.path == "/recalibrate":
            logging.info("Recalibrating")
            calibrated = False
        if self.path == "/snapshot":
            logging.info("Taking snapshot")
            snapshot = True
        if self.path == "/calibration":
            self.send_response(200, "Calibration Image")
            self.send_header("Content-type", "image/png")
            self.end_headers()
            with open(sys.path[0] + "/temp/calibration.png", "rb") as f:
                self.wfile.write(f.read())
            return
        if self.path == "/last_snapshot":
            self.send_response(200, "Calibration Image")
            self.send_header("Content-type", "image/png")
            self.end_headers()
            with open(sys.path[0] + "/temp/snapshot.png", "rb") as f:
                self.wfile.write(f.read())
            return

        self.send_response(200, 'Hello world')
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"""<html>
                         <head><title>Slot car computer</title></head>
                         <body><h2>Slot car computer</h2>
                         <ul>
                         <li><a href="/recalibrate">Recalibrate</a></li>
                         <li><a href="/calibration">Calibration Image</a></li>
                         <li><a href="/snapshot">Take Snapshot</a></li>
                         <li><a href="/last_snapshot">Last snapshot Image</a></li>
                         </ul>
                         </body></html>\n""")
        

    def do_HEAD(self):
        pass

    def do_POST(self):
        pass



if __name__ == "__main__":
    main()