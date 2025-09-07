# CatBeGone

AI-powered cat deterrent system for Raspberry Pi using IMX500 AI camera module.

## Overview

CatBeGone is an automated cat deterrent system that uses computer vision and motion detection to identify cats and play random alert sounds to discourage them from your property. The system combines a PIR motion sensor with an IMX500 AI camera to detect cats with high accuracy and respond with audio deterrents.

## Features

- **AI-powered cat detection** using YOLOv8 neural network on IMX500 camera
- **Motion-triggered activation** via PIR sensor
- **Random audio alerts** from customizable sound library
- **Automatic service management** with systemd
- **Configurable detection parameters** (confidence threshold, timeouts)
- **Built-in cooldown periods** to prevent spam alerts

## Hardware Requirements

- Raspberry Pi (4B recommended)
- IMX500 AI camera module
- PIR motion sensor
- Speaker or audio output device
- MicroSD card (32GB+ recommended)

## Installation

1. Clone this repository to your Raspberry Pi:
```bash
git clone <repository-url>
cd catbegone
```

2. Run the automated setup script:
```bash
chmod +x build.sh
sudo ./build.sh
```

3. Add your custom MP3 alert sounds to the `alerts/` directory

4. Reboot your Pi:
```bash
sudo reboot
```

## Configuration

Edit `catbegone.py` to customize these parameters:

- `motionActivatedWindow`: Duration to scan for cats after motion (default: 30s)
- `cameraFramerate`: Camera FPS for detection (default: 30)
- `confidenceMin`: Minimum confidence for cat detection (default: 0.4)
- `pirPin`: GPIO pin for PIR sensor (default: 8)
- `alertsVolume`: Audio volume level (default: 0.2)
- `timeoutAfterAlert`: Cooldown period after alert (default: 2s)

## File Structure

```
catbegone/
├── catbegone.py          # Main application
├── ai_camera.py          # IMX500 camera interface
├── build.sh              # Installation script
├── alerts/               # MP3 audio files
├── models/               # AI model files
└── README.md            # This file
```

## Usage

The service runs automatically on boot. Manual control:

```bash
# Check status
sudo systemctl status catbegone

# View live logs
sudo journalctl -u catbegone -f

# Stop/start service
sudo systemctl stop catbegone
sudo systemctl start catbegone
```

## How It Works

1. PIR sensor detects motion
2. System activates AI camera for 30 seconds
3. Camera analyzes frames for cat detection
4. When cat detected with >40% confidence, plays random MP3 alert
5. System enters cooldown period
6. Process repeats for next motion event

## Troubleshooting

- Ensure IMX500 model files are in `/usr/share/imx500-models/`
- Check GPIO connections for PIR sensor
- Verify audio device is working: `aplay /usr/share/sounds/alsa/Front_Left.wav`
- Monitor logs for detection accuracy and adjust confidence threshold

## License

This project is for educational and personal use only.