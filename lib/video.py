#!/usr/bin/env python
__author__ = "James Burnett"
__copyright__ = "Copyright (C) James Burnett (https://jamesburnett.io)"
__license__ = "GNU AGPLv3"
__maintainer__ = "James Burnett"
__email__ = "james@jamesburnett.io"
__status__ = "Development"

from threading import Thread
import cv2
import datetime
import time
import numpy as np 
import imutils 

from PIL import Image
from detection import MotionDetection
from detection import HumanDetection
from alerts import Email


class VideoStream(MotionDetection,HumanDetection):

    def __init__(self,source,config):
        print("Starting stream %s" % source["name"])
        #noimg_pil = Image.open('./noimage.jpg')
        #self.noimg_frame = np.array(noimg_pil.getdata())
        self.noimg_frame = cv2.imread('noimage.jpg',0)
        self.source = source
        self.config = config
        self.frame = None
        self.frameOrig = None
        self.thread_stopped = False
        self.frame_counter = 0
        self.status = self.source["name"] + "|starting stream|" 
        self.config = config
        
        self.data = {}
        self.data["uptime"] = 0
        self.data["stream_name"] = self.source["name"]
        self.data["stream_uri"] = self.source["uri"]

        self.email = Email(config["email_server"],config["email_server_username"],config["email_server_password"])
        
        MotionDetection.__init__(self,self.source["fps"])
        
        HumanDetection.__init__(self)

        ###Pre event recording buffer. Keep 400 frames
        self.video_buffer = []

        ###Where to store frames when motion is detected
        self.motion_buffer = []

        #print("%s Initialized." % self.source["name"])


    def start(self):
        Thread(target=self.update, args=()).start()
        return self


    def reconnect(self):
        self.status = self.source["name"] + "|Problem Reading Frames"
        print("Reconnecting %s" % self.source["name"])
        self.rtsp = cv2.VideoCapture(self.source["uri"])
        time.sleep(2.00)


    def get_frame(self,frame):

        frame = imutils.resize(frame, width=640)
        now = datetime.datetime.now()
        strdate = str(now.month) + "-" + str(now.day) + "-" + str(now.year)
        strtime = str(now.hour) + ":" + str(now.minute) + ":" + str(now.second)

        new_frame = frame.copy()

        font                   = cv2.FONT_HERSHEY_SIMPLEX
        fontScale              = 0.50
        lineType               = 1
        cv2.rectangle(new_frame,(0,0),(640,24), (0,0,0), -1)
        cv2.putText(new_frame,str(self.source["name"]), (10,16), font, 0.75,(255,2255,255),2)
        
        v = "{} ".format(self.motion_score)
        

        cv2.putText(new_frame,"M:" + v , (110,14), font, fontScale,(255,2255,255),lineType)
        #cv2.putText(new_frame,str(strdate), (210,14), font, fontScale,(255,255,255),lineType)
        #cv2.putText(new_frame,str(strtime), (340,14), font, fontScale,(255,255,255),lineType)
        return new_frame


    def update(self):

        
        while self.source["offline"] == 1:
            self.data["uptime"] = self.data["uptime"] + 1
            self.frameOrig = self.get_frame(self.noimg_frame)
            #print(self.data["uptime"])
            time.sleep(10)
        

        self.rtsp = cv2.VideoCapture(self.source["uri"])
        print("Video Capture Initialized")

        self.rtsp.set(3,640)
        self.rtsp.set(4,360)
        score_data = []

        motion_started = False

        pre_buffer = []

        write_buffer = []

        time_start = 0.0

        time_diff = 0.0;

        frame_errors = 0

        frame_motion_counter = 0

        while True:

            if self.thread_stopped == True:
                break

            if self.rtsp.isOpened() is False:
                self.reconnect()
                continue

            ret, f = self.rtsp.read()

            if ret is False:
                if frame_errors >= 10:
                    self.rtsp.release()
                frame_errors = frame_errors + 1
                self.status = self.source["name"] + "|Problem Reading Frames|" + str(frame_errors)
                print("Problem reading frames: %d" % frame_errors)
                time.sleep(2)
                continue

            self.frameOrig = self.get_frame(f)

            self.frame = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)

            self.calculate_motion_scores(self.frame)                
            
            ########keep frames for pre-event recording###########
            if len(self.video_buffer) >= 400:
                self.video_buffer.pop()
                self.video_buffer.insert(0,f)
            else:
                self.video_buffer.append(f)
       
           

            if self.motion_detected == True and len(self.motion_buffer) == 0:
                #Motion just detected and motion buffer is empty so lets kick it off with the pre event buffer
                self.motion_buffer = self.video_buffer.copy()
            elif self.motion_detected ==True and len(self.motion_buffer) > 0:
                #Motion detected but motion buffer has frames so lets continue adding frames
                self.motion_buffer.append(f)
            elif self.motion_detected == False and len(self.motion_buffer) > 0:
                #print(len(self.motion_buffer))
                #print(self.motion_buffer[0].shape)
                #Motion is no longer detected but we have frames in the motion buffer so lets save those to a file we can watch.
                now = datetime.datetime.now()
                #fourcc = cv2.VideoWriter_fourcc('M','J','P','G')
                fourcc = cv2.VideoWriter_fourcc(*'FMP4')
                height, width, xx = self.motion_buffer[0].shape
                out = cv2.VideoWriter("c:\temp\test-motion-" + str(time.time()) + ".mkv", fourcc, 4.0, (width,height),True)
                
                self.email.send_email("james@syxalpha.com","jamesburnettva@gmail.com", "Motion Detected " + self.source["name"], "Motion has been detected check\n https://lab.jamesburnett.net:8080/cams.html\n")
                self.email.send_email("james@syxalpha.com","wilderbree3@gmail.com", "Motion Detected " + self.source["name"], "Motion has been detected check\n https://lab.jamesburnett.net:8080/cams.html\n")

                for mf in self.motion_buffer:
                    out.write(mf)
                    #print(mf.shape)
                out.release()

                #Done writing so lets clear the motion buffer for the next motion detection event.
                self.motion_buffer.clear()
                self.video_buffer.clear()

    


        print("Video Thread Existing Worker")
        
    def read(self):
        return self.frame

    def stop(self):
        print("Stopping Video Thread")
        self.thread_stopped = True
        exit()


class VideoPlayer():
        def __init__(self,video_stream):
            self.video_stream = video_stream
            self.thread_stopped = False
            self.debug = False

        def start(self):
            self.video_stream.start()
            Thread(target=self.update, args=()).start()
            return self

        def update(self):
            while True:
                if self.thread_stopped == True:
                    break

                if self.video_stream.frame is not None:
                    try:
                        if self.debug == False:
                            cv2.imshow("Main Frame", self.video_stream.frame)
                        else:
                            cv2.imshow("Debug Frame", self.video_stream.frameDebug)
                    except:
                        print("VideoPlayer Error")
                    key = cv2.waitKey(1) & 0xFF
                    
                    #time.sleep(0.225)
                    

        def stop(self):
            self.thread_stopped = True
            exit()
