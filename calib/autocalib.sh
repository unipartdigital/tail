#!/bin/bash
#
# DW1000 Hat interactive calibration script
#

export HOST=$1
export EUI64=$2

REFS='
  magpi1
  magpi2
  magpi3
  magpi4
  magpi5
  magpi6
  magpi7
  magpi8
'

DIST=${DIST:-2.75}
COUNT=${COUNT:-100}
DELAY=${DELAY:-0.020}
WAIT=${WAIT:-0.5}
PPM_OFFSET=${PPM_OFFSET:-0.0}

TAIL='~/tail/eeprom'

XTALT=16
SPIMAX=20000000

DWTMP="/tmp/dwtmp-$$"
DWLST="/tmp/dwlst-$$"
DWCHS="/tmp/dwchs-$$"

:> ${DWTMP}
:> ${DWLST}

##
## Channel combinations to calibrate
##
## ID,CH,PCODE,PRF,PSR,PWR,COARSE,FINE
##
cat<<MEOW>${DWCHS}
CH7-64,7,20,64,1024,-75,6,6
CH7-16,7,8,16,1024,-75,6,6
CH5-64,5,20,64,1024,-75,3,6
CH5-16,5,8,16,1024,-75,3,6
CH3-64,3,20,64,1024,-75,3,6
CH3-16,3,8,16,1024,-75,3,6
MEOW

##
## Default profile
##
DEFPROF='CH7-64'


##
## Functions
##

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
cat<<MEOW

Usage: $0 <HOST> <EUI64>

MEOW
}

alive()
{
    ping -c 3 -i 0.2 -W 1 -q "$@" 2>/dev/null >/dev/null
}

picheck()
{
    alive ${HOST} && ssh root@${HOST} true 2>/dev/null 2>/dev/null
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
				decawave,antd = <0x4020 0x4020>;
				decawave,xtalt = <${XTALT}>;
				decawave,default = "${DEFPROF}";
				decawave,calib {
MEOW

    N=0
    cat "${DWLST}" | while IFS=, read ID CH PRF ANTD POWER
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
			};
		};
	};

	__overrides__ {
		dw1000_eui = <&dw1000>,"decawave,eui64#0";
		dw1000_profile = <&dw1000>,"decawave,default";
	};
};
MEOW

    dtc -Wno-unit_address_vs_reg -@ -I dts -O dtb -o ${EUI64}.dtbo ${EUI64}.dts
    dtc -Wno-unit_address_vs_reg -@ -I dtb -O dts -o ${EUI64}.dmp ${EUI64}.dtbo
    
    eepmake ${EUI64}.txt ${EUI64}.eep ${EUI64}.dtbo
}

flash()
{
    prepare_dtree

    gzip -c ${EUI64}.eep |
	ssh root@${HOST} "
	    gunzip -c > /tmp/${EUI64}.eep &&
	    flashat /tmp/${EUI64}.eep" ||
	        fail "Remote hat EEPROM programming"
}

remboot()
{
    ssh root@${HOST} reboot 2>/dev/null >/dev/null

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

eui64check()
{
    [[ -n "$1" ]] && [[ "$1" =~ '70b3d5b1e' ]]
}


if ! picheck
then
    mesg "Host ${HOST} is unreachable"
    exit 1
fi
    
if eui64check "${EUI64}"
then
    mesg "Starting initial flashing for ${HOST} <${EUI64}>"
    
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

EUI64=$( ./dwattr.py ${HOST} --print-eui )

if eui64check "${EUI64}"
then
    mesg "Starting calibration process for ${HOST} <${EUI64}>"

    ./calibrate.py *${HOST} ${REFS} -vv --channel=3 --prf=64 --pcode=12 --txpsr=1024 --ppm-offset=${PPM_OFFSET} -X -w ${WAIT} -d ${DELAY} -n ${COUNT} ${EXTRA} > ${DWTMP}

    XTALT=$( cat $DWTMP | egrep '^XTALT' | cut -d' ' -f 3 )
    
    if [[ "${XTALT}" -lt 1 ]] || [[ "${XTALT}" -gt 31 ]]
    then
	fail "XTALT calibration"
    fi
	    
    cat ${DWCHS} | while IFS=, read ID CH PCODE PRF PSR RXPWR COARSE FINE
    do
	if [ -n "${ID}" ]
	then
	    mesg "Calibrating <$ID> CH:${CH} PCODE:${PCODE} PRF:${PRF} PSR:${PSR} Power:${RXPWR}"
	    
	    ./calibrate.py ${HOST}* ${REFS} -vv --channel=${CH} --prf=${PRF} --pcode=${PCODE} --txpsr=${PSR} -T -A -P ${RXPWR} -L ${DIST} -C ${COARSE} -F ${FINE} -w ${WAIT} -d ${DELAY} -n ${COUNT} ${EXTRA} | tee ${DWTMP}
	    
	    TXPWR=$( cat $DWTMP | egrep '^TXPWR' | cut -d' ' -f 3 )
	    ANTDC=$( cat $DWTMP | egrep '^ANTD'  | cut -d' ' -f 3 )
	    
	    if [[ "${ANTDC}" -lt 0x3800 ]] || [[ "${ANTDC}" -gt 0x4400 ]]
	    then
		fail "ANTD calibration"
	    fi

	    echo "$ID,$CH,$PRF,$ANTDC,$TXPWR" >> ${DWLST}
	    echo "Calibration done: ${ID} Ch:${CH} PRF:${PRF} XTALT:${XTALT} PWR:${TXPWR} ANTD:${ANTDC}"
	fi
    done
    
    echo "Programming the DW1000 Hat EEPROM..."
    flash || fail "Flash programming"
    mesg "Programming ${HOST} done."

fi
