#!/bin/env python3

import cv2
from pprint import *
#from picamera2 import Picamera2, Preview
import time
import argparse
from math import *
from statistics import *
import logging

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('infile')
    parser.add_argument('outfile')
    args = parser.parse_args()
    stime = time.time()
    # read the image as grayscale
    src = cv2.imread(args.infile, cv2.IMREAD_COLOR)
    # get geometry
    geometry = TrackGeometry(src)
    print(geometry)
    print(geometry.read_lanes(src))
    geometry.decorate_image(src)
    print(f"Elapsed time: {time.time() - stime}")


class Line:
    def __init__(self, x1, y1, x2, y2):
        self.p1 = (round(x1), round(y1))
        self.p2 = (round(x2), round(y2))
        self.slope = None
        self.angle = None
        self.y_intercept = None
        self.x_intercept = None
        self.horizontal = self.p1[1] == self.p2[1]
        self.vertical = self.p1[0] == self.p2[0]
        self._points = None

        # compute all of the helpful things...
        if self.horizontal:
            self.angle = 0
            self.y_intercept = round(y1)
            self.slope = 0
        elif self.vertical:
            self.angle = 90
            self.x_intercept = round(x1)
            self.slope = 0  # this is really inverse slope.
        else:
            self.slope = ((y2 - y1) / (x2 - x1))
            self.angle = abs(degrees(atan(self.slope)))
            # find the y intercept
            # y = mx + b
            # l[1] = slope * l[0] + y_intercept
            # l[1] - y_intercept = slope * l[0]
            # -y_intercept = slope * l[0] - l[1]
            # y_intercept = -slope * l[0] + l[1]
            y_int = -self.slope * x1 + y1
            if self.angle < 5:
                # horizontal-ish line.  Use the y intercept.
                self.horizontal = True
                self.y_intercept = round(y_int)
            elif abs(self.angle - 90) < 5:
                # vertical-ish line.  Compute x-intercept
                self.vertical = True
                # y = mx + b
                # 0 = slope * x + y_int
                # -y_int = slope * x
                # -y_int / slope = x
                self.x_intercept = round(-y_int / self.slope)
                self.slope = 1/self.slope  # invert the slope

    def __repr__(self):
        return f"Line<{self.p1}-{self.p2} {self.slope}/{self.angle} x@{self.x_intercept} y@{self.y_intercept} {'h' if self.horizontal else ''} {'v' if self.vertical else ''}>"


    def intersection(self, other, bounds=None):
        """Return a tuple that's a coordinate for the intersection of this line
           and other.  If they do not intersect (ever, or within the specified bounds), 
           raise a ValueError"""
        # per https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection        
        x1, y1 = self.p1
        x2, y2 = self.p2
        x3, y3 = other.p1
        x4, y4 = other.p2
        logging.info(f"Computing Intersection of: {self.p1}-{self.p2} and {other.p1}-{other.p2}")
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        px = ((x1 * y2  - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2)* (x3 * y4 - y3 * x4)) / den
        if bounds is not None:
            if px < 0 or py < 0 or px > bounds[0] or py > bounds[1]:
                raise ValueError(f"Point ({px}, {py}) is outside {bounds}")
        logging.info(f"Intersection at ({px}, {py})")
        return (px, py)


    def points(self):
        """Return a list of point tuples for the line"""
        
        if self._points is None:
            logging.info(f"Generating point list for {repr(self)}")
            self._points = []
            if self.angle == 0:
                self._points = [(x, self.p1[1]) for x in range(self.p1[0], self.p2[0] + 1)]
            elif self.angle == 90:
                self._points = [(self.p1[0], y) for y in range(self.p1[1], self.p2[1] + 1)]
            elif self.horizontal:
                self._points = [(self.p1[0] + x, self.p1[1] + x * self.slope) for x in range(abs(self.p1[0] - self.p2[0]) + 1)]
            elif self.vertical:
                self._points = [(self.p1[0] + y * self.slope, self.p1[1] + y) for y in range(abs(self.p1[1] - self.p2[1]) + 1)]
            # round all of the points.
            self._points = [(round(p[0]), round(p[1])) for p in self._points]
            logging.info(f"Points: {self._points}")                
        return self._points


class TrackGeometry:
    def __init__(self, bgrimage):
        """Get track geometry from a BGR image or raise ValueError if it can't be determined"""    
        height, width, depth = bgrimage.shape
        logging.info(f"Calibration Image Shape: {width}, {height}, {depth}")
        gray_image = cv2.cvtColor(bgrimage, cv2.COLOR_BGR2GRAY)
        # run Canny edge detection    
        edge_image = cv2.Canny(gray_image, threshold1=50, threshold2=200, apertureSize=3)
        # get the hough lines
        houghlines = cv2.HoughLinesP(edge_image, rho=1, theta=pi / 180, threshold=50, minLineLength=70, maxLineGap=35)
        if houghlines is None:
            # didn't detect any lines. 
            raise ValueError("Cannot detect track geometry")

        # formalize all the discovered lines
        lines = [Line(*x[0]) for x in houghlines]

        # find the lane dividing line.  It should be the midpoint of the y-intercepts
        ymin = min([x.y_intercept for x in lines if x.horizontal])
        ymax = max([x.y_intercept for x in lines if x.horizontal])
        mp = (ymax + ymin) / 2
        self.lane_divide = Line(0, mp, width, mp)

        # compute each lane's mid line
        self.lanes = []
        y1 = median([x.y_intercept for x in lines if x.horizontal and x.y_intercept < self.lane_divide.y_intercept])
        y2 = y1 + width * median([x.slope for x in lines if x.horizontal and x.y_intercept < self.lane_divide.y_intercept])
        self.lanes.append(Line(0, y1, width, y2))
        y1 = median([x.y_intercept for x in lines if x.horizontal and x.y_intercept > self.lane_divide.y_intercept])
        y2 = y1 + width * median([x.slope for x in lines if x.horizontal and x.y_intercept > self.lane_divide.y_intercept])
        self.lanes.append(Line(0, y1, width, y2))


        # finish line.  Let's assume that traffic is left-to-right.  The finish line is the leftmost
        # vertical line...but sometimes that's not a great line, so we're going to take the
        # average of all of the vertical line X intercepts and the median slope.
        x1 = mean([x.x_intercept for x in lines if x.vertical])
        x2 = x1 + height * median([x.slope for x in lines if x.vertical])
        self.finish_line = Line(x1, 0, x2, height)


        # we need to find the scanning area for each of the lanes.  Length-wise, it'll be half the
        # width between the first lane line and the lane divider.
        self.lane_data = []
        scan_width =  abs(self.lane_divide.y_intercept - self.lanes[0].y_intercept) / 2

        ipoint = self.finish_line.intersection(self.lanes[0], (width, height))
        self.lane_data.append(Line(ipoint[0] - self.finish_line.slope * scan_width / 2, ipoint[1] - scan_width / 2,
                                   ipoint[0] + self.finish_line.slope * scan_width / 2, ipoint[1] + scan_width / 2))

        ipoint = self.finish_line.intersection(self.lanes[1], (width, height))
        self.lane_data.append(Line(ipoint[0] - self.finish_line.slope * scan_width / 2, ipoint[1] - scan_width / 2,
                                   ipoint[0] + self.finish_line.slope * scan_width / 2, ipoint[1] + scan_width / 2))


    def decorate_image(self, src):
        """Draw features onto the source image"""
        # find the lane dividing line
        cv2.line(src, self.lane_divide.p1, self.lane_divide.p2, color=(255, 0, 255))
        
        # draw the two lane centerlines...
        for l in self.lanes:
            cv2.line(src, l.p1, l.p2, color=(255, 255, 0))
        
        # draw the finish line
        cv2.line(src, self.finish_line.p1, self.finish_line.p2, color=(0, 255, 255))
        
        # draw the lane data lines
        for l in self.lane_data:
            cv2.line(src, l.p1, l.p2, color=(255, 0, 0))


    def read_lanes(self, src):
        results = []
        image = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        for l in self.lane_data:
            data = []
            for p in l.points():
                # I /think/ the image data is Y,X rather than X,Y
                data.append(image[p[1], p[0]])
                src[p[1], p[0]] = (255, 128, 128, 255)
            results.append(data)
        return results




if __name__ == "__main__":
    main()