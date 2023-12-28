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
    src = cv2.imread(args.infile, cv2.IMREAD_GRAYSCALE)
    # do canny edge detection
    # args: src image, threshold1, threshold2, edges, aperturesize
    dst = cv2.Canny(src, 50, 200, None, 3)

    geometry = get_geometry(cv2.imread(args.infile, cv2.IMREAD_COLOR))

    # get our destination image
    cdst = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)
    src = cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)
    # get the lines
    hlines = cv2.HoughLinesP(dst, rho=1, theta=pi / 180, threshold=50 , minLineLength=70, maxLineGap=35)
    x_ints = []
    y_ints = []
    lines = []
    if hlines is not None:
        for i in range(len(hlines)):
            l = hlines[i][0]
            # get the angle and intercept
            x_intercept = y_intercept = 0
            slope = None
            if l[0] == l[2]:
                angle = 90
                x_intercept = l[0]                
            elif l[1] == l[3]:
                angle = 0
                y_intercept = l[1]
            else:
                slope = (l[1] - l[3]) / (l[0] - l[2])
                angle = abs(degrees(atan(slope)))
                # find the y intercept
                # y = mx + b
                # l[1] = slope * l[0] + y_intercept
                # l[1] - y_intercept = slope * l[0]
                # -y_intercept = slope * l[0] - l[1]
                # y_intercept = -slope * l[0] + l[1]
                y_int = -slope * l[0] + l[1]

                if abs(angle - 90) < 5:
                    # vertical line, get x intercept
                    # y = mx + b
                    # 0 = slope * x + y_int
                    # -y_int = slope * x
                    # -y_int / slope = x
                    x_intercept = round(-y_int / slope)
                elif abs(angle) < 5:
                    # horizontal line, use y intercept                    
                    y_intercept = round(y_int)

            # get the color
            if angle == 90:
                color = (0, 255, 0)
            elif abs(angle - 90) < 5:
                color = (0, 128, 0)
            elif angle == 0:
                color = (0, 0, 255)
            elif abs(angle) < 5:
                color = (0, 0, 128)
            else:
                color = (0, 128, 128)

            # draw the segment
            cv2.line(src, (l[0], l[1]), (l[2], l[3]), color, 1, cv2.LINE_AA)
            
            # draw the intercept
            cv2.circle(src,(x_intercept, y_intercept), 3, (255, 0, 0))
            if y_intercept == 0:
                # vertical line
                #cv2.line(src, (x_intercept, y_intercept), (round(x_intercept + (1/slope * 480)),480), (255,0, 0))
                pass
            elif x_intercept == 0:
                y_ints.append(y_intercept)


            print(f"{i}: ({l[0]}, {l[1]}), slope={slope}, angle={angle}, intercept=({x_intercept}, {y_intercept})")
            print([x for x in geometry['lines'] if x['p1'] == (l[0], l[1]) or x['p2'] == (l[0], l[1])])

        # find the lane dividing line
        cv2.circle(src, (0, geometry['lane_divide']), radius=3, color=(0, 0, 255))
        # draw the two lanes...
        cv2.line(src, (0, geometry['lane1_point']), (640, round(geometry['lane1_point'] + (geometry['lane1_slope'] * 640))), color=(255, 255, 0))
        cv2.line(src, (0, geometry['lane2_point']), (640, round(geometry['lane2_point'] + (geometry['lane2_slope'] * 640))), color=(255, 255, 0))

        # draw the finish line
        cv2.line(src, (geometry['finish_point'], 0), (round(geometry['finish_point'] + (geometry['finish_slope'] * 480)), 480), (0,255,255))

        print(geometry)
        print(get_lanedata(src, geometry))

        cv2.imwrite(args.outfile, src)
    else:
        print("No lines found")

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
        self.vertical = self.p1[0] == self.p1[0]
        self.points = None

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


    def intersection(self, other, bounds=None):
        """Return a tuple that's a coordinate for the intersection of this line
           and other.  If they do not intersect (ever, or within the specified bounds), 
           raise a ValueError"""
        # per https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection        
        x1, y1 = self.p1
        x2, y2 = self.p2
        x3, y3 = other.p1
        x4, y4 = other.p2
        den = (x1 - x2) * (y3 - y4) - (y1 *- y2) * (x3 - x4)
        px = ((x1 * y2  - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2)* (x3 * y4 - y3 * x4)) / den
        return (px, py)


    def points(self):
        """Return a list of point tuples for the line"""
        if self.points is None:
            self.points = []
            if self.angle == 0:
                self.points = [(x, self.p1[1]) for x in range(abs(self.p1[0] - self.p2[0]) + 1)]
            elif self.angle == 90:
                self.points = [(self.p1[1], y) for y in range(abs(self.p1[1] - self.p2[1]) + 1)]
            elif self.horizontal:
                self.points = [(self.p1[0] + x, self.p1[1] + x * self.slope) for x in range(abs(self.p1[0] - self.p2[0])) + 1]
            elif self.vertical:
                self.points = [(self.p1[0] + y * self.slope, self.p1[1] + y) for y in range(abs(self.p1[1] - self.p2[1])) + 1]
            # round all of the points.
            self.points = [(round(p[0]), round(p[1])) for p in self.points]
                
        return self.points


class TrackGeometry:
    def __init__(self, bgrimage):
        """Get track geometry from a BGR image or raise ValueError if it can't be determined"""    
        width, height = bgrimage.size
        gray_image = cv2.cvtColor(bgrimage, cv2.COLOR_BGR2GRAY)
        # run Canny edge detection    
        edge_image = cv2.Canny(gray_image, threshold1=50, threshold2=200, apertureSize=3)
        # get the hough lines
        houghlines = cv2.HoughLinesP(edge_image, rho=1, theta=pi / 180, threshold=50, minLineLength=70, maxLineGap=35)
        if houghlines is None:
            # didn't detect any lines. 
            raise ValueError("Cannot detect track geometry")

        # formalize all the discovered lines
        lines = [Line(*x) for x in houghlines]

        # find the lane dividing line.  It should be the midpoint of the y-intercepts
        ymin = min([x.y_intercept for x in lines if x.horizontal])
        ymax = max([x.y_intercept for x in lines if x.horizontal])
        mp = (ymax + ymin) / 2
        self.lane_divide = Line(0, mp, width, mp)

        # compute each lane's mid line
        self.lanes = []
        y1 = median([x.y_intercept for x in lines if x.horizontal and x.y_intercept < self.lane_divide.y_intercept])
        y2 = y1 + width * median([x.slope for x in lines if x.horizontal and x.y_intercept < self.lane_divide.y_intercept])
        self.lanes[0] = Line(0, y1, width, y2)
        y1 = median([x.y_intercept for x in lines if x.horizontal and x.y_intercept > self.lane_divide.y_intercept])
        y2 = y1 + width * median([x.slope for x in lines if x.horizontal and x.y_intercept > self.lane_divide.y_intercept])
        self.lanes[1] = Line(0, y1, width, y2)


        # finish line.  Let's assume that traffic is left-to-right.  The finish line is the leftmost
        # vertical line...but sometimes that's not a great line, so we're going to take the
        # average of all of the vertical line X intercepts and the median slope.
        x1 = mean([x.x_intercept for x in lines if x.vertical])
        x2 = x1 + height * median([x.slope for x in lines if x.vertical])
        self.finish_line = Line(x1, 0, x2, height)


        # we need to find the scanning area for each of the lanes.  Length-wise, it'll be half the
        # width between the first lane line and the lane divider.
        self.lane_scan = []
        scan_width =  abs(self.lane_divide.y_intercept - self.lanes[0].y_intercept) / 2

        ipoint = self.finish_line.intersection(self.lanes[0], (width, height))
        self.lane_scan[0] = Line(ipoint[0] - self.finish_line.slope * scan_width / 2, ipoint[1] - scan_width / 2,
                                 ipoint[0] + self.finish_line.slope * scan_width / 2, ipoint[1] + scan_width / 2)

        ipoint = self.finish_line.intersection(self.lanes[0], (width, height))
        self.lane_scan[1] = Line(ipoint[0] - self.finish_line.slope * scan_width / 2, ipoint[1] - scan_width / 2,
                                 ipoint[0] + self.finish_line.slope * scan_width / 2, ipoint[1] + scan_width / 2)


    def decorate_image(self, src):

        # find the lane dividing line
        cv2.circle(src, (0, geometry['lane_divide']), radius=3, color=(0, 0, 255))
        cv2.line(src, (0, geometry['lane_divide']), (640, geometry['lane_divide']), color=(255, 0, 255))
        # draw the two lanes...
        cv2.line(src, (0, geometry['lane1_point']), (640, round(geometry['lane1_point'] + (geometry['lane1_slope'] * 640))), color=(255, 255, 0))
        cv2.line(src, (0, geometry['lane2_point']), (640, round(geometry['lane2_point'] + (geometry['lane2_slope'] * 640))), color=(255, 255, 0))

        # draw the finish line
        cv2.line(src, (geometry['finish_point'], 0), (round(geometry['finish_point'] + (geometry['finish_slope'] * 480)), 480), (0,255,255))

        # draw lane intersections
        cv2.circle(src, geometry['lane1_intersection'], radius=5, color=(128, 128, 255), thickness=2)
        cv2.circle(src, geometry['lane2_intersection'], radius=5, color=(128, 128, 255), thickness=2)

        # draw lane points
        for l in ('lane1', 'lane2'):
            for p in geometry[f'{l}_points']:
                cv2.circle(src, p, radius=1, color=(0, 255, 0))


def get_finishpoints(image, geometry):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    data = []
    for pt in geometry['finish_points']:
        #pxl = image[pt[0], pt[1]]
        data.append(image[pt[0], pt[1]])
    return data


def get_lanedata(image, geometry):
    """Return arrays of pixels """
    data = {}
    for lane in ('lane1', 'lane2'):
        ldata = []
        intercept = geometry[lane + "_point"]
        slope = geometry[lane + "_slope"]
        for x in range(640):
            y = round(intercept + (slope * x))
            # numpy arrays are row, column
            pxl = image[y, x]        
            cval = pxl[0] + pxl[1] * 256 + pxl[2] * 65536
            #ldata.append(f"{cval:06X}")
            ldata.append(cval)
        data[lane] = ldata

    return data


if __name__ == "__main__":
    main()