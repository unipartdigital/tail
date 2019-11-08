#!/bin/bash
#
# DW1000 Hat calibration script
#
# Usage: autocalib.sh INIT|XTALT|BASIC|CALIB <EUI64>
#

##
## Device Under Test - DUT
##
DUT='magpi5'

##
## Reference anchors
##
REFS='
  magpi1
  magpi2
  magpi3
  magpi4
'

##
## Default profile
##
DEFPROF='CH5-12+6'

##
## Calibration profiles
##
## ID,CH,PCODE,PRF,PSR,PWR,COARSE,FINE
##
DWCHS='
CH5-9+3,5,10,64,1024,-9.3,3,8
CH5-9+6,5,10,64,1024,-9.3,6,8
CH5-9+9,5,10,64,1024,-9.3,9,8
CH5-12+0,5,10,64,1024,-12.3,0,8
CH5-12+3,5,10,64,1024,-12.3,3,8
CH5-12+6,5,10,64,1024,-12.3,6,8
CH5-15+0,5,10,64,1024,-15.3,0,8
CH5-15+3,5,10,64,1024,-15.3,3,8
'

##
## Defaults
##

PPM_OFFSET=${PPM_OFFSET:-0.0}

CHANNEL=${CHANNEL:-5}
PCODE=${PCODE:-12}
PRF=${PRF:-64}
PSR=${PSR:-1024}

LEVEL=${LEVEL:--12.3}
DIST=${DIST:-7.90}
COUNT=${COUNT:-100}
DELAY=${DELAY:-0.020}
WAIT=${WAIT:-0.5}
IPVER=${IPVER:-}

XTALT=17
SPIMAX=20000000
ANTD16=0x4000
ANTD64=0x4000


##
## Internal variables
##

DWTMP="/tmp/dwtmp-$$"
DWLST="/tmp/dwlst-$$"

:> ${DWTMP}
:> ${DWLST}

export MODE=$1
export EUI64=$2


##
## Functions
##

mesg()
{
    echo -e "\n*** $*"
}

error()
{
    mesg "$*"
    exit 1
}

fail()
{
    mesg "$* >>FAILED<< miserably."
    exit 1
}

usage()
{
cat<<MEOW

Usage: $0 INIT|XTALT|BASIC|CALIB <EUI64>

MEOW
}

alive()
{
    ping ${IPVER} -c 3 -i 0.2 -W 1 -q "$@" 2>/dev/null >/dev/null
}

picheck()
{
    alive $1 && ssh ${IPVER} root@$1 true 2>/dev/null >/dev/null
}

system_check()
{
    local PIDS=''
    local RET=0
    
    echo -n "Checking system..."
    
    for HOST in ${DUT} ${REFS}
    do
	picheck ${HOST} &
	PIDS+=" ${HOST}:$!"
    done

    for KEY in ${PIDS}
    do
	PID=${KEY##*:}
	HOST=${KEY%%:*}
	wait ${PID} || error "Host ${HOST} not available"
    done

    echo "done"
}

prepare_dtree()
{
    cat<<MEOW >${EUI64}.txt
vendor		"Unipart Digital"
product		"Pi Tail"
product_id	0x1000
product_ver	0x00a0
product_uuid	00000000-0000-0000-0000-000000000000
gpio_drive	0
gpio_slew	0
gpio_hysteresis	0
back_power	0
setgpio		8	ALT0	DEFAULT
setgpio		9	ALT0	DEFAULT
setgpio		10	ALT0	DEFAULT
setgpio		11	ALT0	DEFAULT
setgpio		25	INPUT	DOWN
setgpio		24	INPUT	NONE
setgpio		23	INPUT	NONE
MEOW

    cat<<MEOW >${EUI64}.dts
/dts-v1/;
/plugin/;

/ {
	compatible = "brcm,bcm2708";

	fragment@0 {
		target = <&spi0>;
		__overlay__ {
			status = "okay";
		};
	};

	fragment@1 {
		target = <&spidev0>;
		__overlay__ {
			status = "disabled";
		};
	};

	fragment@2 {
		target = <&gpio>;
		__overlay__ {
			dw1000_pins: dw1000_pins {
				brcm,pins = <23 24 25>;
				brcm,function = <0>;
			};
		};
	};

	fragment@3 {
		target = <&spi0>;
		__overlay__ {
			#address-cells = <1>;
			#size-cells = <0>;
			dw1000: dw1000@0 {
				compatible = "decawave,dw1000";
				reg = <0>;
				pinctrl-names = "default";
				pinctrl-0 = <&dw1000_pins>;
				power-gpio = <&gpio 23 0>;
				reset-gpio = <&gpio 24 6>;
				interrupt-parent = <&gpio>;
				interrupts = <25 4>;
				spi-max-frequency = <${SPIMAX}>;
				decawave,eui64 = /bits/ 64 <0x${EUI64}>;
				decawave,antd = <${ANTD16} ${ANTD64}>;
				decawave,xtalt = <${XTALT}>;
MEOW
    if [ -s "${DWLST}" ]
    then
	cat<<MEOW>>${EUI64}.dts
				decawave,default = "${DEFPROF}";
				decawave,calib {
MEOW

	N=0
	cat "${DWLST}" | while IFS=, read ID CH PRF ANTD POWER REST
	do
	    if [ -n "${ID}" ]
	    then
		cat<<MEOW>>${EUI64}.dts
					calib@$N {
						 id = "${ID}";
						 ch = <${CH}>;
						prf = <${PRF}>;
						antd = <${ANTD}>;
						power = <${POWER}>;
					};
MEOW
		let N+=1
	    fi
	done

	cat<<MEOW>>${EUI64}.dts
				};
MEOW
    fi
    
    cat<<MEOW>>${EUI64}.dts
			};
		};
	};
	__overrides__ {
		dw1000_eui = <&dw1000>,"decawave,eui64#0";
MEOW

    if [ -s "${DWLST}" ]
    then
	cat<<MEOW>>${EUI64}.dts
		dw1000_profile = <&dw1000>,"decawave,default";
MEOW
    fi
    
    cat<<MEOW>>${EUI64}.dts
	};
};
MEOW

    dtc -Wno-unit_address_vs_reg -@ -I dts -O dtb -o ${EUI64}.dtbo ${EUI64}.dts ||
	fail 'Device Tree compilation'
    dtc -Wno-unit_address_vs_reg -@ -I dtb -O dts -o ${EUI64}.dmp ${EUI64}.dtbo ||
	fail 'Device Tree disassembly'
    
    eepmake ${EUI64}.txt ${EUI64}.eep ${EUI64}.dtbo ||
	fail 'EEPROM compilation'
}

flash()
{
    gzip -c ${EUI64}.eep |
	ssh ${IPVER} root@${DUT} "
	    gunzip -c > /etc/${EUI64}.eep &&
	    true /etc/${EUI64}.eep" ||
	        fail "Remote hat EEPROM programming"
}

remboot()
{
    echo -n "Rebooting ${DUT}"
    
    ssh ${IPVER} root@${DUT} reboot 2>/dev/null >/dev/null

    for i in {1..5}
    do
	sleep 1
	echo -n '.'
    done

    for i in {1..100}
    do
	if picheck ${DUT}
	then
	    echo 'done'
	    return 0
	fi
	sleep 0.01
	echo -n '.'
    done

    echo 'fail'
    
    return 1
}

remflash()
{
    mesg "Starting flashing ${DUT} <${EUI64}>"
    
    check_eui64 ${EUI64}
    prepare_dtree
    flash 
    remboot
}

calibrate_xtalt()
{
    ./calibrate.py *${DUT} ${REFS} -X -vv --channel=${CHANNEL} --prf=${PRF} --pcode=${PCODE} --txpsr=${PSR} --ppm-offset=${PPM_OFFSET} -P ${LEVEL} -L ${DIST} -w ${WAIT} -d ${DELAY} -n ${COUNT} ${EXTRA} > ${DWTMP}

    XTALT=$( cat $DWTMP | egrep '^XTALT' | cut -d, -f 3 )
    ANTDC=$( cat $DWTMP | egrep '^ANTD'  | cut -d, -f 3 )
    
    if [[ "${XTALT}" -lt 1 ]] || [[ "${XTALT}" -gt 31 ]]
    then
	fail "XTALT calibration"
    fi
}

calibrate_antd()
{
    ./calibrate.py *${DUT} ${REFS} -A -vv --channel=${CHANNEL} --prf=16 --pcode=${PCODE} --txpsr=${PSR} -P ${LEVEL} -L ${DIST} -w ${WAIT} -d ${DELAY} -n ${COUNT} ${EXTRA} > ${DWTMP}
    
    ANTD16=$( cat $DWTMP | egrep '^ANTD'  | cut -d, -f 3 )
    
    if [[ "${ANTD16}" -lt 0x3900 ]] || [[ "${ANTD16}" -gt 0x4100 ]]
    then
	fail "ANTD PRF16 calibration"
    fi
    
    ./calibrate.py *${DUT} ${REFS} -A -vv --channel=${CHANNEL} --prf=64 --pcode=${PCODE} --txpsr=${PSR} -P ${LEVEL} -L ${DIST} -w ${WAIT} -d ${DELAY} -n ${COUNT} ${EXTRA} > ${DWTMP}
    
    ANTD64=$( cat $DWTMP | egrep '^ANTD'  | cut -d, -f 3 )
    
    if [[ "${ANTD64}" -lt 0x3900 ]] || [[ "${ANTD64}" -gt 0x4100 ]]
    then
	fail "ANTD PRF64 calibration"
    fi
}

calibrate_profiles()
{
    mesg "Starting calibration process for ${DUT} <${EUI64}>"

    EUI64=$( ./dwattr.py ${DUT} --print-eui )

    eui64check "${EUI64}"  || fail "Missing initial programming in DT"

    echo ${DWCHS} | while IFS=, read ID CH PCODE PRF PSR LEVEL COARSE FINE
    do
	if [ -n "${ID}" ]
	then
	    mesg "Calibrating <$ID> CH:${CH} PCODE:${PCODE} PRF:${PRF} PSR:${PSR} Level:${LEVEL}dBm"
	    
	    ./calibrate.py ${DUT}* ${REFS} -T -A -vv --channel=${CH} --prf=${PRF} --pcode=${PCODE} --txpsr=${PSR} -P ${LEVEL} -L ${DIST} -C ${COARSE} -F ${FINE} -w ${WAIT} -d ${DELAY} -n ${COUNT} ${EXTRA} > ${DWTMP}
	    
	    TXPWR=$( cat $DWTMP | egrep '^TXPWR' | cut -d, -f 3 )
	    TXKEY=$( cat $DWTMP | egrep '^TXPWR' | cut -d, -f 4,5 )
	    ANTDC=$( cat $DWTMP | egrep '^ANTD'  | cut -d, -f 3 )
	    
	    if [[ "${ANTDC}" -lt 0x3800 ]] || [[ "${ANTDC}" -gt 0x4400 ]]
	    then
		fail "ANTD calibration"
	    fi

	    P=${TXPWR##0x}
	    POWER=0x$P$P$P$P

	    echo "$ID,$CH,$PRF,$ANTDC,$POWER,$TXKEY,$LEVEL" >> ${DWLST}
	    echo "*** Calibration done: ${ID} Ch:${CH} PRF:${PRF} XTALT:${XTALT} TXPWR:${TXKEY}:${TXPWR} ANTD:${ANTDC}"
	fi
    done
}

check_eui64()
{
    [[ -n "$1" ]] && [[ "$1" =~ '70b3d5b1e' ]] || error "Invalid EUI64: $1"
}

read_eui64()
{
    EUI64=$( ./dwattr.py ${HOST} --print-eui )
    check_eui64 ${EUI64}
}


trap 'echo Interrupt; exit 1' INT HUP

system_check || error "System unavailable"

case "${MODE}" in

    INIT)   remflash
	    ;;
    
    XTALT)  read_eui64
	    calibrate_xtalt
	    remflash
	    ;;
    
    BASIC)  read_eui64
	    calibrate_xtalt
	    calibrate_antd
	    remflash
	    ;;
    
    CALIB)  read_eui64
	    calibrate_xtalt
	    calibrate_antd
    	    calibrate_profiles
	    remflash
	    ;;

    *)      usage
	    ;;
esac

