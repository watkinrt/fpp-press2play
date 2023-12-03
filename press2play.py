from gpiozero import Button, PWMLED
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import json
from jsonschema import validate
import requests
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Timer
from datetime import datetime

# Watchdog flag
watchdog = False

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

# Setup logging
# logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = RotatingFileHandler('/home/fpp/media/logs/press2play.log', maxBytes=20000000, backupCount=5)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


# # Get the hostname, which is used in the MQTT topics
# output = subprocess.run(["hostname"], capture_output=True)
# hostname = output.stdout
# logger.debug(f"FPP hostname: {hostname}")

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
    # "mqtt": {
    #   "type": "object",
    #   "properties": {
    #     "hostname": {
    #         "description": "MQTT broker hostname or IP address",
    #         "type": "string",
    #         "format": "ipv4",
    #         # "oneOf": [
    #         #     { "format": "hostname" },
    #         #     { "format": "ipv4" }
    #         # ]
    #     },
    #     "port": {
    #         "description": "MQTT broker port number",
    #         "type": "integer",
    #         "exclusiveMinimum": 0,
    #         "default": 1883
    #     },
    #     "topic": {
    #         "description": "FPP MQTT topic",
    #         "type": "string",
    #         "default": "FPP"
    #     },
    #   },
    #   "required": ["hostname"]
    # },
    "gpio": {
      "type": "object",
      "properties": {
        "buttonpin": {
            "description": "Button GPIO pin",
            "type": "integer",
            "exclusiveMinimum": 0,
            "maximum": 40,
            "default": 26 
        },
        "ledpin": {
            "description": "LED GPIO pin (required to be PWM compatible)",
            "type": "integer",
            "exclusiveMinimum": 0,
            "maximum": 40,
            "default": 18 
        },
        "debounce": {
            "description": "Button debounce time in seconds",
            "type": "number",
            "inclusiveMinimum": 0,
            "maximum": 1,
            "default": 0.3
        },
      },
      "required": ["buttonpin", "ledpin", "debounce"]
    },
  },
  "required": ["volume", "player", "gpio"]
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
                  "Defaulting to 26.")
    buttonpin = 26

try:
    debounceTime = config['gpio']['debounce']
except KeyError:
    logger.warning("A button debounce time was not found in the config file. "
                  "Defaulting to none.")
    debounceTime = None

try:
    if debounceTime < 0.0001:
        debounceTime = None
except:
    devounceTime = None

button = Button(buttonpin, pull_up=True, bounce_time=debounceTime)

# Create RPi led
try:
    ledpin = config['gpio']['ledpin']
except KeyError:
    logger.warning("An LED GPIO pin was not found in the config file. "
                 "Defaulting to 18.")
    ledpin = 18
led = PWMLED(ledpin)

# Setup Player and Remote MQTT using the REST API
try:
    playerhost = config["player"]
except KeyError:
    logger.warning("An FPP hostname was not found in the config file. "
                 "Defaulting to 'fpp.local'.")
    playerhost = "fpp.local"

def setFppSetting(hostname, setting, value):
    # mqtt": { "description": "MQTT", "settings": [ "MQTTHost", "MQTTPort", "MQTTClientId", "MQTTPrefix", "MQTTUsername", "MQTTPassword", "MQTTCaFile", "MQTTFrequency", "MQTTSubscribe" ] }
    # /api/settings/MQTTHost
    r = requests.put(f"http://{hostname}/api/settings/{setting}", data=f"{value}")
    if "OK" not in r.text:
        raise RuntimeError(f"Unable to set {setting} to {value} on {hostname}")

# Make sure device is set to remote
r = requests.get(f"http://localhost/api/settings/fppMode")
settings = json.loads(r.text)
logger.debug(f"Press2play fpp mode: {settings}.")
if "remote" in settings['value']:
    logger.debug("Already in remote mode.")
else:
    logger.debug("Not in remote mode. Changing from player to remote mode.")
    setFppSetting("localhost", "fppMode", "remote")
    # # Restart FPP for the settings to take hold
    # r = requests.get(f"http://localhost/api/system/fppd/restart")
    # if "OK" not in r.text:
    #     raise RuntimeError(f"Unable to restart FPPD")

# Make sure the primary player is setup to emit multisync packets
try:
    r = requests.get(f"http://{playerhost}/api/settings/MultiSyncEnabled")
    settings = json.loads(r.text)
    logger.debug(f"Player MultiSync mode: {settings}.")
    if settings["value"] == "1":
        logger.debug("Player MultiSync already setup.")
    else:
        logger.debug("Player not emmitting multisync packets. Enabling.")
        setFppSetting(playerhost, "MultiSyncEnabled", "1")
        # # Restart FPP for the settings to take hold
        # r = requests.get(f"http://{playerhost}/api/system/fppd/restart")
        # if "OK" not in r.text:
        #     raise RuntimeError(f"Unable to restart FPPD on player")
except:
    logger.warning("Unable to communicate with player. Skipping MultiSync check.")

def setVolume(volume):
    """ Adjust FPP volume 
    
    Arguments
    ---------
    volume: integer in the range of 0 to 100
        New FPP volume setting
    """
    watchdog = False
    # Make sure volume is in the right form and bounds
    volume = int(volume)
    if volume < 0:
        volume = 0
    elif volume > 100:
        volume = 100

    logger.debug(f"Setting volume to {volume}")
    subprocess.run(['/opt/fpp/src/fpp', '-v', f'{volume}'],
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.STDOUT)

def setStatusLights(status):
    """ Set the kiosk status lights state """
    logger.debug(f"Setting the status lights to {'on' if status else 'off'}")
    watchdog = False
    if status:
        led.blink(on_time=1, off_time=1, fade_in_time=1, fade_out_time=1, background=True)
    else:
        led.off()

def fppdStatus():
    """ Get the currently playing sequence """

    logger.debug("Press2play status requested.")
    # Determine what the current system volume state is, 
    # which can only be queried through the REST api
    r = requests.get("http://localhost/api/fppd/status")
    status = json.loads(r.text)
    logger.debug(f"Press2play status: {status}.")
    return status

def toggleState(log=False):
    """ Toggle the current kiosk state """
    global maxvolume

    logger.debug("Press2play toggle state requested.")
    # Determine what the current system volume state is, 
    # which can only be queried through the REST api
    r = requests.get("http://localhost/api/fppd/volume")
    response = json.loads(r.text)
    volume = int(response['volume'])
    logger.debug(f"Press2play current volume state: {volume}.")
    if volume:
        # If the volume is on, turn it off and set the status lights on
        setStatusLights(True)
        setVolume(0)
    else:
        # If the volume is off, turn it on and turn off the status lights
        setStatusLights(False)
        setVolume(maxvolume)

        # Log the response
        if log:
            with open(Path(__file__).parent / Path("counter.csv"), "a") as f:
                f.write(f"{datetime.now()}, {log}\n")


def onButtonPress():
    """ Update volume and status state when the button is pressed """
    # global maxvolume

    logger.debug("Press2play button pressed.")
    status = fppdStatus()
    if status["current_sequence"]:
        toggleState(log=status["current_sequence"])
    else:
        setVolume(0)
        setStatusLights(False)


def watchdogTimer():
    global watchdog

    if watchdog:
        logger.debug("Watchdog timer hasn't been fed in a while. Turning everything off.")
        setVolume(0)
        setStatusLights(False)
    else:
        watchdog = True

# There isn't any easy way within FPP to blink a GPIO LED (with fading).
# So, we setup and HTTP server here to handle these requets.
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/LED_off':
                # Insert your code here
                setStatusLights(False)
            elif self.path == '/LED_on':
                setStatusLights(True)
            elif self.path == "/state_toggle":
                toggleState()
            elif self.path == "/state_on":
                setStatusLights(False)
                setVolume(maxvolume)
            elif self.path == "/state_off":
                setStatusLights(True)
                setVolume(0)
            
            # Send success status
            self.send_response(200)
        except Exception as ex:
            logger.error(f"Unagle to completed http request '{self.path}': {ex}")
            self.send_response(500)


if __name__ == '__main__':

    # Setup button press callback
    button.when_pressed = onButtonPress

    httpd = HTTPServer(("", 8081), RequestHandler)

    # Set the initial system state
    setVolume(0)
    status = fppdStatus()
    if status["current_sequence"]:
        setStatusLights(True)

    # Setup watchdog timer for 10 minutes
    timer = RepeatTimer(10*60, watchdogTimer)
    timer.start()

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    # Catch exceptions to allow gpiozero to run its cleanup operations
    try:
        httpd.serve_forever()
    except:
        logger.debug("press2play terminated. Cleaning up.")
        setVolume(0)
        setStatusLights(False)