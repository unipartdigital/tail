#!/bin/sh

DEV=$1
[ -z "${DEV}" ] && DEV=/dev/ttyS0

make -C /lib/modules/`uname -r`/build M=`pwd`

killall -q ldattach
sleep 1
rmmod ttytail
modprobe mac802154
insmod ./ttytail.ko
ldattach 29 ${DEV}
sleep 1
PHY=$(basename /sys/class/ieee802154/phy*)
echo "Created ${PHY}"
ip link set wpan0 up
ip link add link wpan0 name lowpan0 type lowpan
ip link set lowpan0 up
