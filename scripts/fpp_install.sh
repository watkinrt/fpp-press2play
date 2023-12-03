#!/bin/bash

# Copy script to FPP scripts directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${SCRIPT_DIR}
cp "press2playRequest.sh" "../../../scripts/"

# Get the root FPP directory
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

