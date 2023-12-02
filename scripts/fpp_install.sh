#!/bin/bash

BASEDIR=$(dirname $0)
cd $BASEDIR
cd ..

# Install python3 and its related dependencies
sudo apt-get update
sudo apt -y install python3 python3-pip
pip install gpiozero rpi-gpio jsonschema

# Notify a restart required
. ${FPPDIR}/scripts/common
setSetting restartFlag 1

