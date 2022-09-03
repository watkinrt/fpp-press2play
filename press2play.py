import paho.mqtt.client as mqtt
from gpiozero import Button, PWMLED
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import requests
from pathlib import Path
import socket
import json

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# logger.setLevel(logging.NOTSET)
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
fhandler = RotatingFileHandler(Path(__file__).parent / Path("fpp-press2play.log"), 
                              maxBytes=100e3,
                              backupCount=2)
fhandler.setLevel(logging.DEBUG)
fhandler.setFormatter(formatter)
logger.addHandler(fhandler)
shandler = logging.StreamHandler()
shandler.setFormatter(formatter)
shandler.setLevel(logging.DEBUG)
logger.addHandler(shandler)
# logging.basicConfig(level=logging.INFO)

# Global FPP status string (falcon/player/{hostname}/status)
fppStatus = ''

# Get the hostname, which is used in the MQTT topics
output = subprocess.run(["hostname"], capture_output=True)
hostname = output.stdout
logger.debug(f"FPP hostname: {hostname}")

# Load config file
configFilename = Path("/home/fpp/media/config/plugin.fpp-press2play")
config = {}
with open(configFilename, "r") as f:
    for line in f:
        var, _ = line.split(" = ")
        value = line.split('"')
        config[var] = value[1]
    
logger.debug(f"Read in config: {config}")

# Pull out the volume
try:
    maxvolume = int(config["press2play_volume"])
    if maxvolume > 100:
        maxvolume = 100
    elif maxvolume < 1:
        maxvolume = 1
except:
    maxvolume = 70
    logger.warning("Output volume was not defined in the config file. "
                  "Defaulting to 70%.")
config["press2play_volume"] = str(maxvolume)

# Create RPi button with specified debouncing time
try:
    buttonpin = int(config['press2play_gpio_buttonpin'])
except:
    logger.warning("A button GPIO pin was not found in the config file. "
                  "Defaulting to 18.")
    buttonpin = 18
config["press2play_gpio_buttonpin"] = str(buttonpin)

try:
    debounceTime = float(config['press2play_gpio_debounce'])
except:
    logger.warning("A button debounce time was not found in the config file. "
                  "Defaulting to 0.3.")
    debounceTime = 0.3
config["press2play_gpio_debounce"] = str(debounceTime)

button = Button(buttonpin, pull_up=True, bounce_time=debounceTime)

# Create RPi led
try:
    ledpin = int(config["press2play_gpio_ledpin"])
except:
    logger.warning("An LED GPIO pin was not found in the config file. "
                 "Defaulting to 26.")
    ledpin = 26
config["press2play_gpio_ledpin"] = str(ledpin)

led = PWMLED(ledpin)

# Setup Player and Remote MQTT using the REST API

try:
    playerhost = config["press2play_playername"]
except:
    logger.warning("playerhost was not found in the config file. "
                 "Defaulting to FPP.")
    playerhost = "FPP"
config["press2play_playername"] = playerhost

try:
    brokername = config["press2play_mqtt_hostname"]
except:
    logger.warning("MQTT broker was not found in the config file. "
                   "Defaulting to localhost.")
    brokername = "localhost"
config["press2play_mqtt_hostname"] = brokername

localhost = socket.gethostname()
if brokername == "localhost" or brokername == "127.0.0.1":
    # Get the MQTT hostname is accessible across the network if local host is specified.
    brokername = localhost+".local"

    # Use localhost portnumber
    portnumber = 1883
else:
    try:
        portnumber = int(config["press2play_mqtt_portnumber"])
    except:
        portnumber = 1883
        logger.warning("MQTT broker port number wasn't specified in the config file. "
                        "Defaulting to 1883.")
config["press2play_mqtt_portnumber"] = str(portnumber)

# Update the config file to be consistent with the error faulted values
with open(configFilename, "w") as f:
    for k, v in config.items():
        f.write(f'{k} = "{v}"\n')

logger.debug(f"Updated config: {config}")

restartFlag = {localhost: False, playerhost: False}

def setFppSetting(hostname, setting, value):
    global restartFlag
    # mqtt": { "description": "MQTT", "settings": [ "MQTTHost", "MQTTPort", "MQTTClientId", "MQTTPrefix", "MQTTUsername", "MQTTPassword", "MQTTCaFile", "MQTTFrequency", "MQTTSubscribe" ] }
    # /api/settings/MQTTHost
    try:
        # Check the curret setting value
        r = requests.get(f"http://{hostname}.local/api/settings/{setting}")
        current = json.loads(r.text)
        if current['value'] == value:
            logger.debug(f"Setting {setting} on {hostname} is already set to {value}.")
            return

        r = requests.put(f"http://{hostname}.local/api/settings/{setting}", data=f"{value}")
        if "OK" not in r.text:
            raise RuntimeError(f"Unable to set {setting} to {value} on {hostname}")
        restartFlag[hostname] = True
    except Exception as ex:
        logger.debug(f"Unable to set {setting} to {value} on {hostname}: {ex}")

# Setup MQTT on primary player instance
setFppSetting(playerhost, "MQTTHost", brokername)
setFppSetting(playerhost, "MQTTPort", portnumber)
setFppSetting(playerhost, "MQTTClientId", "player")
# setFppSetting(playerhost, "MQTTPrefix", topic)

# Make sure the player host is setup as a player and that multisync is enabled
r = requests.get(f"http://{playerhost}.local/api/settings/fppMode")
response = json.loads(r.text)
if response["value"] != "player":
    raise ValueError(f"The specified host system {playerhost} is not set to 'player' mode.")
setFppSetting(playerhost, "MultiSyncEnabled", "1")

# Restart player if a setting was changed
if restartFlag[playerhost]:
    r = requests.get(f"http://{playerhost}.local/api/system/fppd/restart")
    if "OK" not in r.text:
        raise RuntimeError(f"Unable to restart FPP on {playerhost}")

# Make sure the local FPP instance is in remote mode
setFppSetting(localhost, "fppMode", "remote")

# Restart fppd if a setting was changed
if restartFlag[localhost]:
    r = requests.get(f"http://{localhost}.local/api/system/fppd/restart")
    if "OK" not in r.text:
        raise RuntimeError(f"Unable to restart FPP on {localhost}")

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