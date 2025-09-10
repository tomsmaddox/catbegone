from ai_camera import IMX500Detector
from datetime import datetime, timedelta
from picamera2 import Preview
import RPi.GPIO as GPIO
import time
import pygame
import os
import random

motionActivatedWindow = 30 # seconds
cameraFramerate = 30 # fps
confidenceMin = 0.4 # % confidence
pirPin = 13 # gpio pin for pir Sensor
alertsFolder = "/home/tmaddox/catbegone/alerts"
alertsVolume = 0.8
timeoutAfterAlert = 2 # seconds - time allowed for a cat to run away

lastCatDetect = datetime.now()
camera = IMX500Detector()

GPIO.cleanup()
GPIO.setmode(GPIO.BOARD)
GPIO.setup(pirPin, GPIO.IN)

pygame.mixer.init()
pygame.mixer.music.set_volume(alertsVolume) 

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


def startCatDetection():
    #fpsDelay = 1/cameraFramerate
    fpsDelay = 1/5
    global lastCatDetect
    startTime = datetime.now()
    endTime = startTime + timedelta(seconds=motionActivatedWindow)

    camera.start(show_preview=False)

    while datetime.now() < endTime and lastCatDetect < startTime:
        # Small delay to prevent overwhelming the system
        time.sleep(fpsDelay)

        # Get the latest detections
        detections = camera.get_detections()
    
        # Get the labels for reference
        labels = camera.get_labels()
    
        # Process each detection
        for detection in detections:
            label = labels[int(detection.category)]
            confidence = detection.conf

            print(f"object identified: {label}")
            
            # Example: Print when a person is detected with high confidence
            if label == "cat" and confidence > confidenceMin:
                print(f"Cat detected with {confidence:.2f} confidence!")
                lastCatDetect = datetime.now()
                break
        
    camera.stop()

    if (lastCatDetect > startTime):
        print(f"Let's scare that fucker!")
        handleCatProblem()
        time.sleep(timeoutAfterAlert)
        return True
    return False

# Main loop
print('Now waiting for motion')
while True:
    if GPIO.input(pirPin) == True:
        print(f'Motion detected! {datetime.now()}')
        startCatDetection()
    time.sleep(1)
