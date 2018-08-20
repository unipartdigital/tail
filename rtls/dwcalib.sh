#!/bin/bash
#
# DW1000 Hat interactive calibration script
#

HOST=$1
EUI64=$2

XTALT=15
ANTD=0x4000

USER='pi'
TAIL='~/tail/eeprom'

BSS_LIST='bss1 bss2 bss3 bss4 bss5 bss6 bss7 bss8'

export HOST EUI64 XTALT ANTD USER TAIL


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
    ssh ${USER}@${HOST} "make -C ${TAIL} EUI64=${EUI64} XTALT=${XTALT} ANTD16=${ANTD} ANTD64=${ANTD} program" 2>/dev/null >/dev/null
}

remboot()
{
    ssh ${USER}@${HOST} "sudo reboot" 2>/dev/null >/dev/null
}

euicheck()
{
    [[ "$1" =~ '70b3d5b1e' ]]
}


if ! picheck
then
    echo "RPi host ${HOST} is unreachable"
    usage
    exit 1
fi

if [[ -n "${EUI64}" ]]
then
    
    echo "Starting initial flashing for ${HOST} <${EUI64}>"

    if ! euicheck ${EUI64}
    then
	echo "EUI64 argument \"${EUI64}\" is incorrect"
	usage
	exit 1
    fi

    echo "Programming the DW1000 Hat EEPROM..."
    if flash
    then
	echo "Programming successful. Rebooting remotely..."
	remboot
    else
	echo "***"
	echo "*** Programming __FAILED__ miserably."
	echo "***"
	exit 1
    fi

else

    EUI64=$( ./dwattr.py ${HOST} --print-eui )
    echo "Starting calibration process for ${HOST} <${EUI64}>"

    XTALT=$( ./calib-xtalt.py *${HOST} ${BSS_LIST} )
    if [ "${XTALT}" -gt 0 -a "${XTALT}" -lt 31 ]
    then
	echo "XTALT  : ${XTALT}"
    else
	echo "***"
	echo "*** Calibration __FAILED__ miserably."
	echo "***"
	exit 1
    fi

    ANTD=$( ./calib-antd.py *${HOST} ${BSS_LIST} )
    if [[ "${ANTD}" -gt 0x4000 ]] && [[ "${ANTD}" -lt 0x4100 ]]
    then
	echo "ANTD   : ${ANTD}"
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

fi

