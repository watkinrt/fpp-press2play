import paho.mqtt.client as mqtt
from gpiozero import Button, PWMLED
import subprocess
import logging
import json
from jsonschema import validate
import requests
from pathlib import Path
import socket

# Setup logging
logging.basicConfig()
logger = logging.getLogger(__name__)

# Global FPP status string (falcon/player/{hostname}/status)
fppStatus = ''

# Get the hostname, which is used in the MQTT topics
output = subprocess.run(["hostname"], capture_output=True)
hostname = output.stdout
logger.debug(f"FPP hostname: {hostname}")

# Load config file
with open(Path(__file__).parent / Path("config.json"), "r") as f:
    config = json.load(f)
logger.debug(f"Config: {config}")

# Configuration schema
schema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/product.schema.json",
  "title": "press2play configurations schema",
  "description": "Configuration format for press2play options",
  "type": "object",
  "properties": {
    "volume": {
      "description": "Desired music volume in the range 1 to 100",
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 70
    },
    "player": {
        "description": "FPP player hostname",
        "type": "string",
        "default": "fpp.local"
    },
    "mqtt": {
      "type": "object",
      "properties": {
        "hostname": {
            "description": "MQTT broker hostname or IP address",
            "type": "string",
            "format": "ipv4",
            # "oneOf": [
            #     { "format": "hostname" },
            #     { "format": "ipv4" }
            # ]
        },
        "port": {
            "description": "MQTT broker port number",
            "type": "integer",
            "exclusiveMinimum": 0,
            "default": 1883
        },
        "topic": {
            "description": "FPP MQTT topic",
            "type": "string",
            "default": "FPP"
        },
      },
      "required": ["hostname"]
    },
    "gpio": {
      "type": "object",
      "properties": {
        "buttonpin": {
            "description": "Button GPIO pin",
            "type": "integer",
            "exclusiveMinimum": 0,
            "maximum": 40,
            "default": 18 
        },
        "ledpin": {
            "description": "LED GPIO pin (required to be PWM compatible)",
            "type": "integer",
            "exclusiveMinimum": 0,
            "maximum": 40,
            "default": 26 
        },
        "debounce": {
            "description": "Button debounce time in seconds",
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 1,
            "default": 0.3
        },
      },
      "required": ["buttonpin", "ledpin", "debounce"]
    },
  },
  "required": ["volume", "mqtt", "gpio"]
}

# Validate configuration file
validate(instance=config, schema=schema)

# Pull out the volume
try:
    maxvolume = config["volume"]
except:
    maxvolume = 70
    logger.warning("Output volume was not defined in the config file. "
                  "Defaulting to 70%.")

# Create RPi button with specified debouncing time
try:
    buttonpin = config['gpio']['buttonpin']
except KeyError:
    logger.warning("A button GPIO pin was not found in the config file. "
                  "Defaulting to 18.")
    buttonpin = 18

try:
    debounceTime = config['gpio']['debounce']
except KeyError:
    logger.warning("A button debounce time was not found in the config file. "
                  "Defaulting to 0.3.")
    debounceTime = 0.3

button = Button(buttonpin, pull_up=True, bounce_time=debounceTime)

# Create RPi led
try:
    ledpin = config['gpio']['ledpin']
except KeyError:
    logger.warning("An LED GPIO pin was not found in the config file. "
                 "Defaulting to 26.")
    ledpin = 26
led = PWMLED(ledpin)

# Setup Player and Remote MQTT using the REST API
playerhost = config["player"]
try:
    topic = config["mqtt"]["topic"]
except KeyError:
    topic = "FPP"

brokername = config["mqtt"]["hostname"]
if brokername == "localhost" or brokername == "127.0. 0.1":
    # Get the MQTT hostname is accessible across the network if local host is specified.
    brokername = socket.gethostname()+".local"

    # Use localhost portnumber
    portnumber = 1883
else:
    try:
        portnumber = config["mqtt"]["portnumber"]
    except KeyError:
        portnumber = 1883
        logger.warning("MQTT broker port number wasn't specified in the config file. "
                        "Defaulting to 1883.")

def setFppSetting(hostname, setting, value):
    # mqtt": { "description": "MQTT", "settings": [ "MQTTHost", "MQTTPort", "MQTTClientId", "MQTTPrefix", "MQTTUsername", "MQTTPassword", "MQTTCaFile", "MQTTFrequency", "MQTTSubscribe" ] }
    # /api/settings/MQTTHost
    r = requests.put(f"http://{hostname}.local/api/settings/{setting}", data=f"{value}")
    if "OK" not in r.text:
        raise RuntimeError(f"Unable to set {setting} to {value} on {hostname}")

# Setup MQTT on primary player instance
setFppSetting(playerhost, "MQTTHost", brokername)
setFppSetting(playerhost, "MQTTPort", portnumber)
setFppSetting(playerhost, "MQTTClientId", "player")
# setFppSetting(playerhost, "MQTTPrefix", topic)

# Restart FPP for the settings to take hold
r = requests.get(f"http://{playerhost}.local/api/system/fppd/restart")
if "OK" not in r.text:
    raise RuntimeError(f"Unable to restart FPP on {playerhost}")

def setVolume(volume):
    """ Adjust FPP volume 
    
    Arguments
    ---------
    volume: integer in the range of 0 to 100
        New FPP volume setting
    """

    # Make sure volume is in the right form and bounds
    volume = int(volume)
    if volume < 0:
        volume = 0
    elif volume > 100:
        volume = 100

    logger.debug(f"Setting volume to {volume}")
    subprocess.run(['/opt/fpp/src/fpp', '-v', f'{volume}'])

def setStatusLights(status):
    """ Set the kiosk status lights state """
    logger.debug(f"Setting the status lights to {'on' if status else 'off'}")
    if status:
        led.blink(on_time=1, off_time=1, fade_in_time=1, fade_out_time=1, background=True)
    else:
        led.off()

# The callback for when the client receives a CONNACK response from the server.
def onConnect(client, userdata, flags, rc):
    logger.debug(f"Connected to MQTT broker with result code {rc}")

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    topic = f"falcon/player/{playerhost}/status"
    client.subscribe(topic)
    logger.debug(f"Subscribed to {topic} on {playerhost}")

    topic = f"falcon/player/{playerhost}/playlist/sectionPosition/status"
    client.subscribe(topic)
    client.subscribe(topic)
    logger.debug(f"Subscribed to {topic} on {playerhost}")

# The callback for when a PUBLISH message is received from the server.
def onMessage(client, userdata, msg):
    global fppStatus
    logger.debug(msg.topic+" "+str(msg.payload))
    if msg.topic == f"falcon/player/{playerhost}/status":
        # FPP player state changed.
        fppStatus = msg.payload.decode()
        if 'playing' in fppStatus:
            # FPP switched to playing. Make sure the volume is off
            # and that the kiosk is on
            logger.debug("FPP started playing.")
            setVolume(0)
            setStatusLights(True)
        else:
            # Otherwise, make sure the volume is off and the status lights are on
            logger.debug("FPP is no longer playing.")
            setVolume(0)
            setStatusLights(False)
    elif msg.topic == f"falcon/player/{playerhost}/playlist/sectionPosition/status" and fppStatus == "playing":
        # FPP song changed.
        songNumber = int(msg.payload.decode())
        logger.debug("FPP song changed.")
        setVolume(0)
        setStatusLights(True)

def onButtonPress():
    """ Update volume and status state when the button is pressed """
    global maxvolume

    logger.debug("Press2play button pressed.")
    # Turn on FPP volume
    setVolume(maxvolume)

    # Turn off FPP status lights
    setStatusLights(False)

if __name__ == '__main__':

    # Setup button press callback
    button.when_pressed = onButtonPress

    # Setup MQTT client to track FPP events
    client = mqtt.Client()
    client.on_connect = onConnect
    client.on_message = onMessage
    client.connect(brokername, portnumber, 60)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    # Catch exceptions to allow gpiozero to run its cleanup operations
    try:
        client.loop_forever()
    except:
        logger.debug("press2play terminated. Cleaning up.")