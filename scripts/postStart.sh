#!/bin/sh

BASEDIR=$(dirname $0)
cd $BASEDIR
cd ..

# Note, we start the process with bash so that we can name it.
echo "Starting the Press2Play Plugin Backend"
bash -c "exec -a press2play python3 press2play.py &"
