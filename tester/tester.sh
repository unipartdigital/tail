#!/bin/sh

cd "$(dirname "$0")"

sudo systemctl lightdm stop
./tester.py
sudo systemctl lightdm start
