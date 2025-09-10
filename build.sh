#!/bin/bash

# Raspberry Pi Cat Deterrent Setup Script

set -e  # Exit on any error

echo "Setting up Cat Deterrent service..."

sudo apt update && sudo apt full-upgrade -y
sudo apt install -y imx500-all python3-opencv python3-munkres
sudo apt install vim git

# Install and set up i2s amp
sudo apt install python3-venv
python -m venv env --system-site-packages
source env/bin/activate
sudo apt install -y wget
pip3 install adafruit-python-shell
wget https://github.com/adafruit/Raspberry-Pi-Installer-Scripts/raw/main/i2samp.py
sudo -E env PATH=$PATH python3 i2samp.py

# Get the current directory (where cat_deterrent.py should be located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="catbegone"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PYTHON_PATH=$(which python3)

# Install models
cp $SCRIPT_DIR/models/*.rpk /usr/share/imx500-models/

# Check if catbegone.py exists
if [ ! -f "$SCRIPT_DIR/catbegone.py" ]; then
    echo "Error: catbegone.py not found in $SCRIPT_DIR"
    exit 1
fi

# Create systemd service file
echo "Creating systemd service file..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Cat Deterrent Service
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=pi
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_PATH $SCRIPT_DIR/catbegone.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions on the service file
sudo chmod 644 "$SERVICE_FILE"

# Reload systemd and enable the service
echo "Enabling and starting the service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# Add cron job to restart service every 30 minutes
echo "Setting up cron job for service restart every 30 minutes..."
CRON_JOB="*/30 * * * * /bin/systemctl restart $SERVICE_NAME"

# Check if cron job already exists, if not add it
(sudo crontab -l 2>/dev/null | grep -v "$SERVICE_NAME"; echo "$CRON_JOB") | sudo crontab -

# Verify the service is running
#sudo systemctl start "$SERVICE_NAME"
#echo "Checking service status..."
#sudo systemctl status "$SERVICE_NAME" --no-pager

echo "Cat Deterrent service setup complete!"
echo "Service will start automatically on boot and restart every 30 minutes."
echo ""
echo "Useful commands:"
echo "  Check status: sudo systemctl status $SERVICE_NAME"
echo "  Stop service: sudo systemctl stop $SERVICE_NAME"
echo "  Start service: sudo systemctl start $SERVICE_NAME"
echo "  View logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "reboot is required."