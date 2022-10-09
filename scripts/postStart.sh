#!/bin/sh

# Make sure the audio is off
/opt/fpp/src/fpp -v 0

BASEDIR=$(dirname $0)
cd $BASEDIR
cd ..

echo "Starting the Press2Play Plugin Backend"
python3 press2play.py &
