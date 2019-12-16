#!/bin/sh

cd "$(dirname "$0")"

sudo systemctl stop lightdm
sudo pigpiod
#sudo chgrp pi /sys/kernel/config/device-tree/overlays
#sudo chmod g+w /sys/kernel/config/device-tree/overlays
sudo -E ./tester.py
sudo systemctl start lightdm
