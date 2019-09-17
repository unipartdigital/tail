#!/bin/bash
#
# DW1000 Hat interactive calibration script
#
# Usage: autocalib.sh HOST <EUI64>
#

export HOST=$1
export EUI64=$2

XTALT=17
SPIMAX=20000000
ANTD16=0x4000
ANTD64=0x4000

DWTMP="/tmp/dwtmp-$$"

:> ${DWTMP}


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
				decawave,antd = <${ANTD16} ${ANTD64}>;
				decawave,xtalt = <${XTALT}>;
			};
		};
	};

	__overrides__ {
		dw1000_eui = <&dw1000>,"decawave,eui64#0";
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

    ssh root@${HOST} dmesg | fgrep dw1000
fi

