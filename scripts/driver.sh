#!/bin/bash

pan_id=0x1234

set -e
set -x

make -C /lib/modules/`uname -r`/build M=~/kernel
sync
sudo rmmod dw1000_mod || true
sync
sudo modprobe mac802154
sudo modprobe hwmon
sudo insmod ~/pps_core.ko || true
sudo insmod ~/ptp.ko || true
sudo insmod ~/kernel/dw1000_mod.ko
short_addr=0x$(cut -d: -f7-8 /sys/class/net/wpan0/address | sed s/://)
sudo iwpan wpan0 set pan_id ${pan_id}
sudo iwpan wpan0 set short_addr ${short_addr}
sudo ip link add link wpan0 name lowpan0 type lowpan
sudo ip link set wpan0 up
sudo ip link set lowpan0 up

set +x
ip addr show wpan0
ip addr show lowpan0
