#!/bin/sh

DEV=$1
[ -z "${DEV}" ] && DEV=/dev/ttyS0

make -C /lib/modules/`uname -r`/build M=`pwd`

sudo killall -q ldattach
sleep 1
sudo rmmod ttytail
sudo modprobe mac802154
sudo insmod ./ttytail.ko
sudo ldattach 29 ${DEV}
while true ; do
    echo "Waiting for PHY creation..."
    sleep 1
    PHY=$(basename /sys/class/ieee802154/phy*)
    if [ "${PHY}" != "phy*" ] ; then
	echo "Created ${PHY}"
	break
    fi
done
sudo ip link set wpan0 up
sudo ip link add link wpan0 name lowpan0 type lowpan
sudo ip link set lowpan0 up
