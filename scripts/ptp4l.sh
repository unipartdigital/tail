#!/bin/sh

set -e
set -x

make -C ~/linuxptp
sync
sudo ~/linuxptp/ptp4l -f /etc/linuxptp/ptp4l.conf -i lowpan0 -6 -m
