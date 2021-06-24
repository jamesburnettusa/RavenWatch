#!/usr/bin/env python
__author__ = "James Burnett"
__copyright__ = "Copyright (C) James Burnett (https://jamesburnett.io)"
__license__ = "GNU AGPLv3"
__maintainer__ = "James Burnett"
__email__ = "james@jamesburnett.io"
__status__ = "Development"

import cv2
import imutils
import numpy
import time



class HumanDetection:
    
    def __init__(self):
        self.enable_human_detection = True
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.human_detection_weight = 0.0
        
    def calculate_human_detection(self,frame):
        frame = cv2.resize(frame,(320,240))

        tframe = frame.copy()

        rects, weights = self.hog.detectMultiScale(tframe,winStride=(20,20),padding=(16,16), scale=1.01, useMeanshiftGrouping=False)
                
        for i, (x, y, w, h) in enumerate(rects):
            #cv2.rectangle(self.framePeople, (x,y), (x+w,y+h),(0,255,0),2)
            self.human_detection_weight = weights[i][0]
             



class MotionDetection:

    def __init__(self,fps):
    
        self.motion_score = 0

        self.motion_detected = False

        self.frame_buffer = []

        self.fps = fps

        self.frameDelta = None

        self.frameDebug = None
      
        self.time_last = 0

        
        self.motion_timer = 0


    def calculate_motion_scores(self,frame):
 
        if self.frameDelta is None:
            self.frameDelta = frame

        if len(self.frame_buffer) >= self.fps:
            self.frame_buffer.pop()
            self.frame_buffer.insert(0,frame)
        else:
            self.frame_buffer.append(frame)

     
        self.frameDelta = cv2.absdiff(self.frame_buffer[0],self.frame_buffer[len(self.frame_buffer) - 1])

        self.frameDelta = cv2.GaussianBlur(self.frameDelta, (5, 5), 0)

        self.frameDebug = self.frameDelta

        thresh = cv2.threshold(self.frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

        thresh = cv2.erode(thresh, None, iterations=2)

        thresh = cv2.dilate(thresh, None, iterations=2)

        cnts,heirarchy = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

        color = (255, 255, 255) 

        area = 0

        if len(cnts) != 0:
            c = max(cnts, key = cv2.contourArea)

            x,y,w,h = cv2.boundingRect(c)

            cv2.rectangle(self.frameOrig, (x, y), (x+w, y+h), color, 2)

            area = cv2.contourArea(c)
        
        if area > 0 and area != self.motion_score:
            self.motion_score = area

        if self.motion_score > 4000 and self.motion_detected == False:
            self.motion_detected = True
            self.motion_timer = time.time()
        
        if self.motion_detected == True:
            if self.motion_score > 4000:
                self.motion_timer = time.time()

            elapsed = time.time() - self.motion_timer

            if self.motion_score < 1000 and elapsed > 5.0:
                self.motion_detected = False
                self.frame_buffer.clear()


        
    




