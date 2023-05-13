#!/bin/sh

BASEDIR=$(dirname $0)
cd $BASEDIR
cd ..

echo "Starting the Press2Play Plugin Backend"
python3 press2play.py