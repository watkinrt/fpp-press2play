#!/bin/sh

echo "Stopping the Press2Play Plugin Backend"
pkill --euid fpp --signal TERM --full press2play