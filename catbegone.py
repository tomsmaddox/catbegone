from ai_camera import IMX500Detector
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

import cv2
import numpy as np

from picamera2 import CompletedRequest, MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics
from picamera2.devices.imx500.postprocess import softmax



motionActivatedWindow = 20 # seconds
cameraFramerate = 30 # fps
confidenceMin = 0.4 # % confidence
pirPin = 13 # gpio pin for pir Sensor
alertsFolder = "/home/tmaddox/catbegone/alerts"
alertsVolume = 0.8
timeoutAfterAlert = 2 # seconds - time allowed for a cat to run away


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


"""def parseClassificationResults():
    fpsDelay = 1/cameraFramerate
    startTime = datetime.now()
    endTime = startTime + timedelta(seconds=motionActivatedWindow)

    print(f"lastcatalert: {lastCatAlert}")

    camera.start(Preview.NULL)

    print(f"lastcatalert: {lastCatAlert}")
    
    while datetime.now() < endTime:
        # Get the latest detections
        detections = camera.get_detections()
    
        # Get the labels for reference
        labels = camera.get_labels()
    
        # Process each detection
        for detection in detections:
            label = labels[int(detection.category)]
            confidence = detection.conf

            print(f"object identified {label}")
            
            # Example: Print when a person is detected with high confidence
            if label == "cat" and confidence > confidenceMin:
                print(f"Cat detected with {confidence:.2f} confidence!")
                print(f"Let's scare that fucker!")
                handleCatProblem()
                lastCatAlert = datetime.now()
                break
        
        # Small delay to prevent overwhelming the system
        time.sleep(fpsDelay)

    print(f"lastcatalert: {lastCatAlert}")
    if (lastCatAlert > startTime): time.sleep(timeoutAfterAlert)
    return lastCatAlert > startTime"""

def getDetections():
        """Get the latest detections"""
        global last_detections
        return last_detections

def getLabel(request: CompletedRequest, idx: int) -> str:
    """Retrieve the label corresponding to the classification index."""
    global LABELS
    if LABELS is None:
        LABELS = imx500.network_intrinsics.labels
        assert len(LABELS) in [1000, 1001], "Labels file should contain 1000 or 1001 labels."
        output_tensor_size = imx500.get_output_shapes(request.get_metadata())[0][0]
        if output_tensor_size == 1000:
            LABELS = LABELS[1:]  # Ignore the background label if present
    return LABELS[idx]

def getLabels():
    """Get the list of detection labels"""
    labels = imx500.network_intrinsics.labels
    if intrinsics.ignore_dash_labels:
        labels = [label for label in labels if label and label != "-"]
    return labels

def parseClassificationResults(request: CompletedRequest) -> List[Detection]:
    """Parse the output tensor into the classification results above the threshold."""
    global last_detections

    bbox_normalization = imx500.network_intrinsics.bbox_normalization
    threshold = 0.55
    iou = 0.65
    max_detections = 10

    np_outputs = imx500.get_outputs(request.get_metadata(), add_batch=True)
    input_w, input_h = imx500.get_input_size()

    if np_outputs is None:
        last_detections = []
        return last_detections
    
    #if imx500.network_intrinsics.postprocess == "nanodet":
    #    boxes, scores, classes = postprocess_nanodet_detection(
    #        outputs=np_outputs[0], 
    #        conf=threshold, 
    #        iou_thres=iou,
    #        max_out_dets=max_detections
    #    )[0]
    #    from picamera2.devices.imx500.postprocess import scale_boxes
    #    boxes = scale_boxes(boxes, 1, 1, input_h, input_w, False, False)
    #else:
    scores, classes = np_outputs[1][0], np_outputs[2][0]
    #    if bbox_normalization:
    #        boxes = boxes / input_h
    #    boxes = np.array_split(boxes, 4, axis=1)
    #    boxes = zip(*boxes)

    last_detections = [
        Detection(category, score)
        for score, category in zip(scores, classes)
        if score > threshold
    ]

    return last_detections

def getArgs():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, help="Path of the model",
                        default="/usr/share/imx500-models/imx500_network_yolov8n_pp.rpk")
    parser.add_argument("--fps", type=int, help="Frames per second")
    parser.add_argument("-s", "--softmax", action=argparse.BooleanOptionalAction, help="Add post-process softmax")
    parser.add_argument("-r", "--preserve-aspect-ratio", action=argparse.BooleanOptionalAction,
                        help="preprocess the image with preserve aspect ratio")
    parser.add_argument("--labels", type=str,
                        help="Path to the labels file")
    parser.add_argument("--print-intrinsics", action="store_true",
                        help="Print JSON network_intrinsics then exit")
    return parser.parse_args()

if __name__ == "__main__":
    global lastCatAlert
    lastCatAlert = datetime.now()

    args = getArgs()

    GPIO.cleanup()
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(pirPin, GPIO.IN)

    pygame.mixer.init()
    pygame.mixer.music.set_volume(alertsVolume)

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

    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration(controls={"FrameRate": intrinsics.inference_rate}, buffer_count=12)
    imx500.show_network_fw_progress_bar()

    print('Now waiting for motion')
    while True:
        if GPIO.input(pirPin) == True:
            print(f'Motion detected! {datetime.now()}')
            
            startTime = datetime.now()
            endTime = startTime + timedelta(seconds=motionActivatedWindow)

            picam2.start(config, show_preview=False)
            if intrinsics.preserve_aspect_ratio:
                imx500.set_auto_aspect_ratio()
            # Register the callback to parse and draw classification results
            picam2.pre_callback = parseClassificationResults


            while endTime > datetime.now():
                # Get the latest detections
                detections = getDetections()

                # Get the labels for reference
                labels = getLabels()

                # Process each detection
                for detection in detections:
                    label = labels[int(detection.category)]
                    confidence = detection.conf

                    print(f"object identified {label}")

                    # Example: Print when a person is detected with high confidence
                    if label == "cat" and confidence > confidenceMin:
                        print(f"Cat detected with {confidence:.2f} confidence!")
                        print(f"Let's scare that fucker!")
                        handleCatProblem()
                        lastCatAlert = datetime.now()
                        break

                time.sleep(0.5)
            
            print(f'Ending motion detection, returning to PIR sensor')
            picam2.stop()

        time.sleep(0.5)
