from ai_camera import IMX500Detector
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import time
import pygame
import os
import random

motionActivatedWindow = 30 # seconds
cameraFramerate = 30 # fps
confidenceMin = 0.4 # % confidence
pirPin = 8 # gpio pin for pir Sensor
alertsFolder = "/home/pi/catbegone/alerts"
alertsVolume = 0.2
timeoutAfterAlert = 2 # seconds - time allowed for a cat to run away

lastCatAlert = datetime.now()
camera = IMX500Detector()

GPIO.setmode(GPIO.BOARD)
GPIO.setup(pirPin, GPIO.IN)
time.sleep(2)

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
    fpsDelay = 1/cameraFramerate
    startTime = datetime.now()
    endTime = startTime + timedelta(seconds=motionActivatedWindow)

    camera.start()
    
    while datetime.now() < endTime:
        # Get the latest detections
        detections = camera.get_detections()
    
        # Get the labels for reference
        labels = camera.get_labels()
    
        # Process each detection
        for detection in detections:
            label = labels[int(detection.category)]
            confidence = detection.conf
            
            # Example: Print when a person is detected with high confidence
            if label == "cat" and confidence > confidenceMin:
                print(f"Cat detected with {confidence:.2f} confidence!")
                print(f"Let's scare that fucker!")
                handleCatProblem()
                lastCatAlert = datetime.now()
                break
        
        # Small delay to prevent overwhelming the system
        time.sleep(fpsDelay)

    if lastCatAlert > startTime: time.sleep(timeoutAfterAlert)
    return lastCatAlert > startTime

# Main loop
while True:
    if GPIO.input(pirPin) == True:
        print('Motion detected!')
        startCatDetection()
