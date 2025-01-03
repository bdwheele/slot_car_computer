#!/bin/env python3
import argparse
import logging
import cv2
from picamera2 import Picamera2
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
from PIL import Image
import io
from math import pi
from statistics import mean
import time
from string import Template
import numpy
import threading

PIX_W = 160
PIX_H = 120

#camera = Picamera2()
#camera.configure(camera.create_video_configuration(main={'size': (PIX_W, PIX_H), 'format': 'BGR888'}))
#camera.start()

lane_y = [None, None]
finish_line = int(PIX_W / 2)

static_images = {}
live_image = None


class SyncedCamera:
    def __init__(self):
        self.camera = Picamera2()
        self.camera.configure(self.camera.create_video_configuration(main={'size': (PIX_W, PIX_H), 'format': 'BGR888'}))
        self.camera.start()
        self.lock = threading.Lock()
        self.image = None
        self.timestamp = 0

    def camera_thread(self):
        while True:
            self.lock.acquire()
            self.timestamp = time.time()
            self.image = self.camera.capture_array()        
            self.lock.release()

    def get_image(self):
        self.lock.acquire()
        x = numpy.copy(self.image)
        self.lock.release()
        return x


camera = SyncedCamera()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loglevel", choices=['INFO', 'DEBUG', 'WARNING', 'ERROR'], default='INFO', help="Logging level")
    args = parser.parse_args()


    print("Starting camera thread")
    camera_thread = threading.Thread(target=camera.camera_thread)
    camera_thread.start()

    print("Calibrating lanes..")
    calibrate_lanes()

    print("Serving...")
    with StreamingServer(("", 8080), Handler) as httpd:
        httpd.serve_forever()


class StreamingServer(socketserver.ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def template(file, values=None):
    if values is None:
        values = {} 
    with open(file) as f:
        tmplate = Template(f.read())
    return tmplate.safe_substitute(values)


def main_page(req: BaseHTTPRequestHandler):
    if req.command == 'GET':
        req.send_response(200)
        req.send_header('content-type', 'text/html')
        req.end_headers()
        req.wfile.write(bytes(template("main.html"), 'utf-8'))
    else:
        req.send_response_only(401)



def live_page(req: BaseHTTPRequestHandler):
    pass







def calibration(req: BaseHTTPRequestHandler):
    if req.command == 'POST':
        calibrate_lanes()
        req.send_response(302)
        req.send_header('Location', '/')
        req.end_headers()
    else:
        req.send_response_only(401)


def static_image(req: BaseHTTPRequestHandler):    
    image_name = req.path.split('/')[3]
    if image_name in static_images:
        buffer = io.BytesIO()
        Image.fromarray(static_images[image_name]).save(buffer, 'JPEG')
        image = buffer.getvalue()
        req.send_response(200)
        req.send_header('Content-type', 'image/jpeg')
        req.send_header('Content-length', len(image))
        req.end_headers()
        req.wfile.write(image)
    else:
        req.send_response_only(404)    


def live_image(req: BaseHTTPRequestHandler):
    def decorate_image(bgrimage):
            for y in lane_y:
                if y is not None:
                    cv2.line(bgrimage, (0, y), (PIX_W, y), color=(255, 0, 255))
            cv2.line(bgrimage, (finish_line, 0), (finish_line, PIX_H), color=(0, 255, 0))

    req.send_response(200)
    req.send_header('Age', 0)
    req.send_header('Cache-Control', 'no-cache, private')
    req.send_header('Pragma', 'no-cache')
    req.send_header('Content-type', 'multipart/x-mixed-replace; boundary=FRAME')
    req.end_headers()
    try:
        count = 0
        stime = time.time()
        while True:            
            #image_array = camera.capture_array()
            image_array = camera.get_image()
            decorate_image(image_array)                
            img = Image.fromarray(image_array)
            buffer = io.BytesIO()
            img.save(buffer, 'JPEG')
            image = buffer.getvalue()
            req.wfile.write(b'--FRAME\r\n')
            req.send_header('Content-type', 'image/jpeg')
            req.send_header('Content-length', len(image))
            req.end_headers()
            req.wfile.write(image)
            req.wfile.write(b'\r\n')
            count += 1
            if count % 100 == 0:
                print(f"Average time per frame: {(time.time() - stime)/count}")


    except Exception as e:
        logging.exception(f"Error with client {req.client_address}: {e}")




def calibrate_lanes():
    #calibration_image = static_images['calibration'] = camera.capture_array()
    calibration_image = static_images['calibration'] = camera.get_image()
    decorated_calibration_image = static_images['decorated_calibration'] = numpy.copy(static_images['calibration'])    
    print(calibration_image)
    gray_image = cv2.cvtColor(calibration_image, cv2.COLOR_BGR2GRAY)
    # run Canny edge detection    
    edge_image = cv2.Canny(gray_image, threshold1=50, threshold2=200, apertureSize=3)
    # get the hough lines
    houghlines = cv2.HoughLinesP(edge_image, rho=1, theta=pi / 180, threshold=50, minLineLength=70, maxLineGap=35)
    lane_data = [[], []]
    if houghlines is not None:        
        for g in houghlines:                
            for s in g:
                if abs(s[0] - s[2]) > PIX_W/3 and abs(s[1] - s[3]) < 5:
                    # horizontal line!
                    print(s)
                    y = mean([s[1], s[3]])
                    if y < PIX_H / 2:
                        lane_data[0].append(y)
                    else:
                        lane_data[1].append(y)
                    cv2.line(decorated_calibration_image, (s[0], s[1]), (s[2], s[3]), color=(0, 255, 255))
    
        try:
            for i, l in enumerate(lane_data):
                y = mean(l)
                lane_y[i] = y
                cv2.line(decorated_calibration_image, (0, y), (PIX_W, y), color=(255, 0, 255))
        except Exception as e:
            pass




class Handler(BaseHTTPRequestHandler):
    routes = {
        '/': main_page,
        '/image/static/': static_image,
        '/image/live': live_image,
        '/calibration': calibration,
        '/live': live_page,
    }
    
    def do_GET(self):
        for prefix in sorted(self.routes.keys(), key=lambda x: len(x), reverse=True):
            if self.path.startswith(prefix):
                print(f"Calling prefix: {prefix} for {self.path}")
                self.routes[prefix](self)
                break
        else:
            self.send_response_only(500)

    do_POST = do_GET        


if __name__ == "__main__":
    main()