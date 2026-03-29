#!/bin/bash
echo "Installing system dependencies..."
apt update
apt install -y python3 python3-pip build-essential libffi-dev python3-dev

echo "Installing Python dependencies from requirements.txt..."
pip3 install -r requirements.txt --break-system-packages

echo "Setup complete. Run 'python3 -m backend.main' to start the panel."
