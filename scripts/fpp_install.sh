#!/bin/bash

# Install python3 and its related dependencies
# sudo apt-get update
# sudo apt -y install python3 python3-pip
# pip install gpiozero rpi-gpio paho-mqtt jsonschema

# Enable the MQTT broker service for subsequent reboots
sudo systemctl enable mosquitto.service

# Makesure MQTT is accessible by other hosts on the network
# https://randomnerdtutorials.com/how-to-install-mosquitto-broker-on-raspberry-pi/
MOSQUITTO_CONFIG=/etc/mosquitto/mosquitto.conf
if grep -q "listener 1883" "$MOSQUITTO_CONFIG"; then
  echo "Mosquitto listener port already configured."
else
  echo "Mosquitto listener port missing from configuration. Adding to end of $MOSQUITTO_CONFIG"
  echo "listener 1883" | sudo tee -a $MOSQUITTO_CONFIG
fi

if grep -q "allow_anonymous true" "$MOSQUITTO_CONFIG"; then
  echo "Mosquitto listener port already configured."
else
  echo "Mosquitto allow_anonymous missing from configuration. Adding to end of $MOSQUITTO_CONFIG"
  echo "allow_anonymous true" | sudo tee -a $MOSQUITTO_CONFIG
fi

# Start the service
sudo systemctl restart mosquitto.service



