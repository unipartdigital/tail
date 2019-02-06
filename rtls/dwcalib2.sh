#!/bin/bash
#
# DW1000 Hat interactive calibration script
#

HOST=$1
EUI64=$2

REF_LIST='
	magpi1.pinet
	magpi2.pinet
	magpi3.pinet
	magpi4.pinet
	magpi5.pinet
	magpi6.pinet
	magpi7.pinet
	magpi8.pinet
'

DIST=${DIST:-4.25}
RXPWR=${RXPWR:--75}
COUNT=${COUNT:-100}
DELAY=${DELAY:-0.020}
WAIT=${WAIT:-0.5}

CHANNEL=${CHANNEL:-3}
PCODE=${PCODE:-20}
PRF=${PRF:-64}
RATE=${RATE:-850}
TXPSR=${TXPSR:-1024}
TXPWR=${TXPWR:-6+5}
XTALT=${XTALT:-16}
ANTD=${ANTD:-0x4050}

ANTD16=${ANTD}
ANTD64=${ANTD}
ANTDIF=18

USER='pi'
TAIL='~/tail/eeprom'

RES="/tmp/dwcalib-$$.res"


export HOST EUI64


mesg()
{
	echo "***"
	echo "*** $*"
	echo "***"
}

fail()
{
	mesg "$* >>FAILED<< miserably."
	exit 1
}

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

refconfig()
{
    ./dwattr.py -vvs \
	    --channel ${CHANNEL}        \
            --pcode ${PCODE}            \
            --prf ${PRF}                \
            --rate ${RATE}              \
            --txpsr ${TXPSR}            \
            --smart_power 0             \
            --tx_power ${TXPWR}         \
            --antd cal                  \
            --xtalt cal                 \
	    ${REF_LIST}
}

dutconfig()
{
    ./dwattr.py -vvs \
            --channel ${CHANNEL}        \
            --pcode ${PCODE}            \
            --prf ${PRF}                \
            --rate ${RATE}              \
            --txpsr ${TXPSR}            \
            --smart_power 0             \
            --tx_power ${TXPWR}         \
            --antd ${ANTD}              \
            --xtalt ${XTALT}            \
	    ${HOST}
}

start-anchor()
{
    ssh ${USER}@${HOST} "sudo systemctl start anchor"
    sleep 3
}

flash()
{
    ssh ${USER}@${HOST} "make -C ${TAIL} EUI64=${EUI64} XTALT=${XTALT} ANTD16=${ANTD16} ANTD64=${ANTD64} program" >/dev/null
}

remboot()
{
    ssh ${USER}@${HOST} "sudo reboot" 2>/dev/null >/dev/null

    sleep 5
    
    N=60
    while ! picheck ${HOST}
    do
	let N-=1
	test $N -lt 1 && return 1
	sleep 1
    done
    
    return 0
}

euicheck()
{
    [[ "$1" =~ '70b3d5b1e' ]]
}


if ! picheck
then
    echo "Host ${HOST} is unreachable"
    usage
    exit 1
fi


if [[ -n "${EUI64}" ]]
then
    mesg "Starting initial flashing for ${HOST} <${EUI64}>"

    if ! euicheck ${EUI64}
    then
	echo "EUI64 argument \"${EUI64}\" is invalid"
	usage
	exit 1
    fi

    echo "Programming the DW1000 Hat EEPROM..."
    if ! flash
    then
	fail "Initial programming"
    fi

    echo "Initial programming successful. Rebooting remotely..."
    if ! remboot
    then
	fail "Remote reboot"
    fi
fi


if picheck
then
    EUI64=$( ./dwattr.py ${HOST} --print-eui )
    
    mesg "Starting calibration process for ${HOST} <${EUI64}>"

    refconfig
    dutconfig

    ./calibrate.py *${HOST} ${REF_LIST} -T -X -A -R -P ${RXPWR} -L ${DIST} -w ${WAIT} -d ${DELAY} -n ${COUNT} -vv > ${RES}

    TXPWR=$( cat $RES | egrep '^TXPWR' | cut -d' ' -f 3 )
    XTALT=$( cat $RES | egrep '^XTALT' | cut -d' ' -f 3 )
    ANTDC=$( cat $RES | egrep '^ANTD'  | cut -d' ' -f 3 )

    if [[ "${XTALT}" -lt 1 ]] || [[ "${XTALT}" -gt 31 ]]
    then
	fail "XTALT calibration"
    fi

    if [[ "${ANTDC}" -lt 0x4000 ]] || [[ "${ANTDC}" -gt 0x4200 ]]
    then
	fail "ANTD calibration"
    fi

    echo "Calibration done: ${TXPWR} ${XTALT} ${ANTDC}"
    
    ANTD64=${ANTDC}
    ANTD16=$((${ANTDC}-${ANTDIF}))
    
    echo "Programming the DW1000 Hat EEPROM..."
    if ! flash
    then
	fail "Flash programming"
    fi

    mesg "Programming ${HOST} done."

fi
