#!/usr/bin/python3

from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import time
import pygame
import os
import random

import argparse
import sys
import time
from typing import List

from picamera2 import CompletedRequest, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics

motionActivatedWindow = 30 # seconds
cameraFramerate = 30 # fps
confidenceMin = 0.4 # % confidence
pirPin = 13 # gpio pin for pir Sensor
alertsFolder = "/home/tmaddox/catbegone/alerts"
alertsVolume = 1
timeoutAfterAlert = 2 # seconds - time allowed for a cat to run away

#Picamera2.set_logging(Picamera2.DEBUG)
#os.environ["LIBCAMERA_LOG_LEVELS"] = "DEBUG"

imx500 = None
picam2 = None
last_detections = []
LABELS = None

class Detection:
    def __init__(self, category, conf):
        """Create a Detection object, recording the bounding box, category and confidence."""
        self.category = category
        self.conf = conf

def handleCatProblem():
    """Play a random MP3 file from the alerts folder at full volume."""
    
    # Check if alerts folder exists
    if not os.path.exists(alertsFolder):
        print(f"Warning: {alertsFolder} folder not found!")
        return
    
    # Get all MP3 files in the alerts folder
    mp3Files = [f for f in os.listdir(alertsFolder) if f.lower().endswith('.mp3')]
    
    if not mp3Files:
        print(f"Warning: No MP3 files found in {alertsFolder} folder!")
        return
    
    # Select a random MP3 file
    randomMp3 = random.choice(mp3Files)
    mp3Path = os.path.join(alertsFolder, randomMp3)
    
    print(f"Playing alert: {randomMp3}")
    
    # Load and play the MP3 file
    pygame.mixer.music.load(mp3Path)
    pygame.mixer.music.play()
    
    # Wait for the audio to finish playing
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    
    print(f"Alert finished playing")

def getDetections():
        """Get the latest detections"""
        global last_detections
        return last_detections

def getLabels():
    """Get the list of detection labels"""
    labels = imx500.network_intrinsics.labels
    if intrinsics.ignore_dash_labels:
        labels = [label for label in labels if label and label != "-"]
    return labels

def parseClassificationResults(request: CompletedRequest) -> List[Detection]:
    """Parse the output tensor into the classification results above the threshold."""
    global last_detections

    threshold = confidenceMin
    np_outputs = imx500.get_outputs(request.get_metadata(), add_batch=True)

    if np_outputs is None:
        last_detections = []
        return last_detections
    
    scores, classes = np_outputs[1][0], np_outputs[2][0]

    last_detections = [
        Detection(category, score)
        for score, category in zip(scores, classes)
        if score > threshold
    ]

    return last_detections

def startDetection(intrinsics):
    global lastCatAlert
    startTime = datetime.now()
    endTime = startTime + timedelta(seconds=motionActivatedWindow)

    with Picamera2(imx500.camera_num) as picam2:
        config = picam2.create_preview_configuration(controls={"FrameRate": intrinsics.inference_rate}, buffer_count=12)
        imx500.show_network_fw_progress_bar()

        picam2.start(config, show_preview=False)
        time.sleep(1)

        if intrinsics.preserve_aspect_ratio:
            imx500.set_auto_aspect_ratio()
        # Register the callback to parse and draw classification results
        picam2.pre_callback = parseClassificationResults


        while datetime.now() < endTime and lastCatAlert < startTime:
            # Get the latest detections
            detections = getDetections()

            # Get the labels for reference
            labels = getLabels()

            # Process each detection
            for detection in detections:
                label = labels[int(detection.category)]
                confidence = detection.conf

                print(f"object identified {label}")

                # Alert when a cat is detected with high confidence
                if label == "cat":
                    print(f"Cat detected with {confidence:.2f} confidence!")
                    print(f"Let's scare that fucker!")
                    handleCatProblem()
                    lastCatAlert = datetime.now()
                    break

            time.sleep(0.5)
    
        print(f'Ending motion detection, returning to PIR sensor')
        picam2.stop()

def getArgs():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, help="Path of the model",
                        default="/usr/share/imx500-models/imx500_network_yolov8n_pp.rpk")
    parser.add_argument("--fps", type=int, help="Frames per second")
    parser.add_argument("-r", "--preserve-aspect-ratio", action=argparse.BooleanOptionalAction,
                        help="preprocess the image with preserve aspect ratio")
    parser.add_argument("--labels", type=str,
                        help="Path to the labels file")
    parser.add_argument("--print-intrinsics", action="store_true",
                        help="Print JSON network_intrinsics then exit")
    return parser.parse_args()

if __name__ == "__main__":
    global lastCatAlert
    args = getArgs()

    # This must be called before instantiation of Picamera2
    imx500 = IMX500(args.model)
    intrinsics = imx500.network_intrinsics
    if not intrinsics:
        intrinsics = NetworkIntrinsics()
        intrinsics.task = "object detection"
    elif intrinsics.task != "object detection":
        print("Network is not an object detection task", file=sys.stderr)
        exit()
    # Override intrinsics from args
    for key, value in vars(args).items():
        if key == 'labels' and value is not None:
            with open(value, 'r') as f:
                intrinsics.labels = f.read().splitlines()
        elif hasattr(intrinsics, key) and value is not None:
            setattr(intrinsics, key, value)
    # Defaults
    if intrinsics.labels is None:
        with open("assets/coco_labels.txt", "r") as f:
            intrinsics.labels = f.read().splitlines()
    intrinsics.update_with_defaults()

    if args.print_intrinsics:
        print(intrinsics)
        exit()

    lastCatAlert = datetime.now()

    GPIO.cleanup()
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(pirPin, GPIO.IN)

    pygame.mixer.init()
    pygame.mixer.music.set_volume(alertsVolume)

    print('Now waiting for motion')
    while True:
        if GPIO.input(pirPin) == True:
            print(f'Motion detected! {datetime.now()}')
            
            startDetection(intrinsics)

        time.sleep(0.5)
