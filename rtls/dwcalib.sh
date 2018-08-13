#!/bin/bash
#
# DW1000 Hat interactive calibration script
#

HOST=$1
EUI64=$2

USER='pi'
EDIR='~/tail/eeprom'

BSS_LIST='bss1 bss2 bss3 bss4 bss5 bss6 bss7 bss8'


usage()
{
cat <<EOM

Usage: $0 <HOST> <EUI64>

EOM
}

alive()
{
    ping -c 3 -i 0.2 -W 1 -q "$@" 2>/dev/null >/dev/null
}

picheck()
{
    alive ${HOST} && ssh ${USER}@${HOST} true 2>/dev/null 2>/dev/null
}

flash()
{
    ssh ${USER}@${HOST} "make -C ${EDIR} EUI64=${EUI64} XTALT=${XTALT} program" 2>/dev/null >/dev/null
}

euicheck()
{
    [[ "${EUI64}" =~ '70b3d5b1e' ]]
}


if ! picheck
then
    echo "RPi host ${HOST} is unreachable"
    usage
    exit 1
fi

if ! euicheck
then
    echo "EUI64 argument \"${EUI64}\" is incorrect"
    usage
    exit 1
fi


echo "Starting calibration process for ${HOST}..."

XTALT=$( ./calib-xtalt.py *${HOST} ${BSS_LIST} )

if [ "${XTALT}" -gt 0 -a "${XTALT}" -lt 31 ]
then
    echo "XTALT: ${XTALT}"
else
    echo "***"
    echo "*** Calibration __FAILED__ miserably."
    echo "***"
    exit 1
fi

echo "Programming the DW1000 Hat EEPROM..."
if flash
then
    echo "Programming successful."
else
    echo "***"
    echo "*** Programming __FAILED__ miserably."
    echo "***"
    exit 1
fi

