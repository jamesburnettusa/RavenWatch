#!/usr/bin/env python
__author__ = "James Burnett"
__copyright__ = "Copyright (C) James Burnett (https://jamesburnett.io)"
__license__ = "GNU AGPLv3"
__maintainer__ = "James Burnett"
__email__ = "james@jamesburnett.io"
__status__ = "Development"  

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import threading

import os
import io
import sys
import json
from PIL import Image
import time
#import StringIO


class Handler(BaseHTTPRequestHandler):
            
    def do_POST(self):

        if self.path == "/debug":

            message = "none"
            self.send_response(200)

            self.send_header("Content-Type","image/jpeg")
        
            self.end_headers()
            
            self.wfile.write(message)
        return


    def get_file(self,path):
        name, ext = os.path.splitext(self.path.split("?")[0])
        file = self.path.split("?")[0]
        if ext == ".css":
            return [file,"text/css",ext,name]
        elif ext == ".js":
            return [file,"application/javascript",ext,name]
        elif ext == ".html":
            return [file,"text/html",ext,name]
        elif ext == ".jpg":
            return [file,"image/jpeg",ext,name]
        elif ext == ".png":
            return [file,"image/png",ext,name]  
        elif ext == ".sjpg":
            return [file,"image/jpeg",ext,name]          
        elif ext == ".djpg":
            return [file,"image/jpeg",ext,name]          
        else:
            return [file,"text/plain",ext,name]
    

    def do_GET(self):

        
        ###Some useful variables
        ### self.requestpath - the full request path with GET/POST command
        ### self.path - Just the path requested (html file etc)
        ### self.command - The command. Is this a GET or POST etc?
        ### self.headers - A list of headers.
        
        http_file = self.get_file(self.path)
        
        message = None

        buffer = bytearray()

        try:
            doc = self.server.DocumentRoot + "/" + http_file[0]

            content_type = http_file[1]
            
            ext = http_file[2]

            if self.path == "/cams":
                f=open(self.server.DocumentRoot + "/cams.html", "r")
                message = f.read()
                buffer.extend(map(ord, message))

             
            ######Process Motion JPEG
            elif ext == ".mjpg":
                
                stream_file = http_file[3].split("_")
                cam_number = int(stream_file[1])
                                
                self.send_response(200)
                self.send_header('Age', 0)
                self.send_header('Cache-Control', 'no-cache, private')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Content-type','multipart/x-mixed-replace; boundary="jpgboundary"')
                self.end_headers()
                
                while True:
                    frame = self.server.streams[cam_number].frameOrig
                    if frame is not None:
                        jpg = Image.fromarray(frame)
                        img_io = io.BytesIO()
                        jpg.save(img_io,'JPEG')
                        img_io.seek(0)
                        self.wfile.write("--jpgboundary\r\n".encode())
                        self.send_header('Content-type','image/jpeg')
                        #self.send_header('Content-length',str(img_io.getbuffer().nbytes))
                        self.end_headers()

                        self.wfile.write(img_io.read())
                        #jpg.save(self.wfile,'JPEG')
                        self.wfile.write("\r\n".encode())
                        
                        time.sleep(0.05)
                        
           
            elif ext == ".html" or ext == ".js" or ext == ".css":
                f=open(doc, "r")
                message = f.read()
                buffer.extend(map(ord, message))

            elif ext == ".png" or ext == ".jpg":
                f=open(doc, "rb")
                message = f.read()
                buffer.extend(message)

            elif ext == ".sjpg" or ext == ".djpg" :  #CAN REMOVE THIS AT SOME POINT WE NOW US /frame/0    /frame/1 etc to get image data from stream.
                stream_file = http_file[3].split("_")
                cam_number = int(stream_file[1])
                #print(stream_file[1])
                if ext == ".sjpg":
                    frame = self.server.streams[cam_number].frameOrig
                elif ext == ".djpg":
                    frame = self.server.streams[cam_number].frameDebug

                if frame is not None:
                    img = Image.fromarray(frame)
                    img_io = io.BytesIO()
                    img.save(img_io, 'JPEG', quality=70)
                    img_io.seek(0)
                    message = img_io.read()           
                    buffer.extend(message)
            else:
                print("Unknown or not found File: %s" % self.path)

            self.send_response(200)
            self.send_header("Content-Type",content_type)
            self.end_headers()
            self.wfile.write(buffer)
                 
        except FileNotFoundError:
            message = "404 file not found." + doc
            print(message)
        except BrokenPipeError:
            print("Broken Pipe")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)   
            print(message)
        return
    
    def log_message(self, format, *args):
        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    stream = None
    streams = []
    DocumentRoot = None
    time_start = 0
    data = {}
    data["stream_count"] = 0
    data["system_uptime"] = 0.0
    data["streams"] = []
    
    def init(self, DocumentRoot):
        self.thread_stopped = False
        self.DocumentRoot = DocumentRoot
       
    def serve_forever(self):
        while 1:
            if self.thread_stopped == True:
                break
            self.handle_request()

    def start_streams(self):
        self.data["stream_count"] = len(self.streams)
        for stream in self.streams:
            self.data["streams"].append(stream.data)
            stream.start()
        


    def setup(self):
        print("setup")

### for ssl
#httpd.socket = ssl.wrap_socket (httpd.socket, 
#        keyfile="path/to/key.pem", 
#        certfile='path/to/cert.pem', server_side=True)

    def stop(self):
        self.server_close()
        self.thread_stopped = True
        for stream in self.streams:
            stream.stop()

        print("Closing HTTP Sockets")
        self.server.socket.close()
        print("Stopping HTTP Server")
        self.server.server_close()
        exit()
