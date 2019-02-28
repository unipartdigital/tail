#!/bin/sh

cd "$(dirname "$0")"

sudo systemctl stop lightdm
sudo pigpiod
./tester.py
sudo systemctl start lightdm
