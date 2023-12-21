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


def decorate_with_geometry(src, geometry):
    # find the lane dividing line
    cv2.circle(src, (0, geometry['lane_divide']), radius=3, color=(0, 0, 255))
    cv2.line(src, (0, geometry['lane_divide']), (640, geometry['lane_divide']), color=(255,255, 0))
    # draw the two lanes...
    cv2.line(src, (0, geometry['lane1_point']), (640, round(geometry['lane1_point'] + (geometry['lane1_slope'] * 640))), color=(255, 255, 0))
    cv2.line(src, (0, geometry['lane2_point']), (640, round(geometry['lane2_point'] + (geometry['lane2_slope'] * 640))), color=(255, 255, 0))

    # draw the finish line
    cv2.line(src, (geometry['finish_point'], 0), (round(geometry['finish_point'] + (geometry['finish_slope'] * 480)), 480), (0,255,255))

    


def get_geometry(bgrimage):
    """Get track geometry from a BGR image or return None if it can't be determined"""
    g_image = cv2.cvtColor(bgrimage, cv2.COLOR_BGR2GRAY)
    # run Canny edge detection    
    e_image = cv2.Canny(g_image, threshold1=50, threshold2=200, apertureSize=3)
    # get the hough lines
    hlines = cv2.HoughLinesP(e_image, rho=1, theta=pi / 180, threshold=50, minLineLength=70, maxLineGap=35)
    if hlines is None:
        # didn't detect any lines. 
        return None

    # compute a bunch of data for each of the lines found.
    lines = []
    for hline in hlines:
        x1, y1, x2, y2 = hline[0]
        line = {
            'p1': (x1, y1),
            'p2': (x2, y2),
            'isHorizontal': y1 == y2,
            'isVertical': x1 == x2,
            'slope': None,
            'angle': None,
            'x_intercept': None,
            'y_intercept': None
        }

        # compute angle, slope, and intercept
        if line['isHorizontal']:
            line['angle'] = 0
            line['y_intercept'] = y1
            line['slope'] = 0
        elif line['isVertical']:
            line['angle'] = 90
            line['x_intercept'] = x1
            line['slope'] = 0  # this is really inverse slope.
        else:
            line['slope'] = ((y2 - y1) / (x2 - x1))
            line['angle'] = abs(degrees(atan(line['slope'])))
            # find the y intercept
            # y = mx + b
            # l[1] = slope * l[0] + y_intercept
            # l[1] - y_intercept = slope * l[0]
            # -y_intercept = slope * l[0] - l[1]
            # y_intercept = -slope * l[0] + l[1]
            y_int = -line['slope'] * x1 + y1
            if line['angle'] < 5:
                # horizontal-ish line.  Use the y intercept.
                line['isHorizontal'] = True
                line['y_intercept'] = round(y_int)
            elif abs(line['angle'] - 90) < 5:
                # vertical-ish line.  Compute x-intercept
                line['isVertical'] = True
                # y = mx + b
                # 0 = slope * x + y_int
                # -y_int = slope * x
                # -y_int / slope = x
                line['x_intercept'] = round(-y_int / line['slope'])
                line['slope'] = 1/line['slope']  # invert the slope
        lines.append(line)
        
    # Now that the lines are identified, start laying out the track geometry.
    geometry = {
        'lines': lines,        
    }

    # find the lane dividing line.  It should be the median of all of the 
    # y-intercepts, offset by the 
    ymin = min([x['y_intercept'] for x in lines if x['isHorizontal']])
    ymax = max([x['y_intercept'] for x in lines if x['isHorizontal']])
    geometry['lane_divide'] = round((ymax + ymin) / 2)

    # get each lane's intercept and slope...
    geometry['lane1_point'] = round(median([x['y_intercept'] for x in lines if x['isHorizontal'] and x['y_intercept'] < geometry['lane_divide']]))
    geometry['lane1_slope'] = median([x['slope'] for x in lines if x['isHorizontal'] and x['y_intercept'] < geometry['lane_divide']])
    geometry['lane2_point'] = round(median([x['y_intercept'] for x in lines if x['isHorizontal'] and x['y_intercept'] > geometry['lane_divide']]))
    geometry['lane2_slope'] = median([x['slope'] for x in lines if x['isHorizontal'] and x['y_intercept'] > geometry['lane_divide']])
    
    # finish line.  Let's assume that traffic is left-to-right.  The finish line is the leftmost
    # vertical line
    geometry['finish_point'] = round(min([x['x_intercept'] for x in lines if x['isVertical']]))
    geometry['finish_slope'] = median([x['slope'] for x in lines if x['isVertical']])
    
    geometry['finish_points'] = [(y, round(geometry['finish_point'] + (geometry['finish_slope'] * y))) for y in range(480)]
    logging.info(f"Finish width: {geometry['finish_slope'] * 480}")
    return geometry

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