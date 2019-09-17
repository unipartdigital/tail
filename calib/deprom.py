#!/usr/bin/python3

import os
import sys
import math
import ctypes
import struct
import argparse

from pprint import pprint


##
## DW1000 Device Tree
##

DW1000_SYSDT = '/sys/firmware/devicetree/base/soc/spi@7e204000/dw1000@0/'

def GetDTAttr(attr):
    with open(DW1000_SYSDT + attr, 'rb') as f:
        value = f.read()
    return value

def GetDTAttrStr(attr):
    with open(DW1000_SYSDT + attr, 'r') as f:
        value = f.read()
    return value.rstrip('\n\r\0')


def read_dtree():
    DT = {}
    val = struct.unpack('>II', GetDTAttr('decawave,antd'))
    DT['ANTD16'] = '0x{:04x}'.format(val[0])
    DT['ANTD64'] = '0x{:04x}'.format(val[1])
    val = struct.unpack('>Q', GetDTAttr('decawave,eui64'))
    DT['EUI64'] = '{:016x}'.format(val[0])
    val = struct.unpack('>I', GetDTAttr('decawave,xtalt'))
    DT['XTALT'] = '{:d}'.format(val[0])
    val = GetDTAttrStr('decawave,default')
    DT['DEFAULT'] = val
    val = struct.unpack('>I', GetDTAttr('spi-max-frequency'))
    DT['SPIMAX'] = '{:d}'.format(val[0])
    
    DT['CALIB'] = {}
    for i in range(24):
        cal = 'calib@{:d}'.format(i)
        try:
            key = 'decawave,calib/{}/name'.format(cal)
            val = GetDTAttrStr(key)
            DT['CALIB'][cal] = {}
            DT['CALIB'][cal]['NAME'] = cal
            key = 'decawave,calib/{}/id'.format(cal)
            val = GetDTAttrStr(key)
            DT['CALIB'][cal]['ID'] = '{}'.format(val)
            key = 'decawave,calib/{}/ch'.format(cal)
            val = struct.unpack('>I', GetDTAttr(key))
            DT['CALIB'][cal]['CH'] = '{:d}'.format(val[0])
            key = 'decawave,calib/{}/prf'.format(cal)
            val = struct.unpack('>I', GetDTAttr(key))
            DT['CALIB'][cal]['PRF'] = '{:d}'.format(val[0])
            key = 'decawave,calib/{}/power'.format(cal)
            val = struct.unpack('>I', GetDTAttr(key))
            DT['CALIB'][cal]['POWER'] = '0x{:08x}'.format(val[0])
            key = 'decawave,calib/{}/antd'.format(cal)
            val = struct.unpack('>I', GetDTAttr(key))
            DT['CALIB'][cal]['ANTD'] = '0x{:04x}'.format(val[0])
        except:
            pass
            
    return DT

    
def prepare_dtree(dtree):
    str = '''
/dts-v1/;
/plugin/;

/ {{
        compatible = "brcm,bcm2708";

        fragment@0 {{
                target = <&spi0>;
                __overlay__ {{
                        status = "okay";
                }};
        }};

        fragment@1 {{
                target = <&spidev0>;
                __overlay__ {{
                        status = "disabled";
                }};
        }};

        fragment@2 {{
                target = <&gpio>;
                __overlay__ {{
                        dw1000_pins: dw1000_pins {{
                                brcm,pins = <23 24 25>;
                                brcm,function = <0>;
                        }};
                }};
        }};

        fragment@3 {{
                target = <&spi0>;
                __overlay__ {{
                        #address-cells = <1>;
                        #size-cells = <0>;
                        dw1000: dw1000@0 {{
                                compatible = "decawave,dw1000";
                                reg = <0>;
                                pinctrl-names = "default";
                                pinctrl-0 = <&dw1000_pins>;
                                power-gpio = <&gpio 23 0>;
                                reset-gpio = <&gpio 24 6>;
                                interrupt-parent = <&gpio>;
                                interrupts = <25 4>;
                                spi-max-frequency = <{SPIMAX}>;
                                decawave,eui64 = /bits/ 64 <0x{EUI64}>;
                                decawave,antd = <{ANTD16} {ANTD64}>;
                                decawave,xtalt = <{XTALT}>;
                                decawave,default = "{DEFAULT}";
                                decawave,calib {{
'''.format(**dtree)

    for key in sorted(dtree['CALIB']):
        str += '''
                                       {NAME} {{
                                                id = "{ID}";
                                                ch = <{CH}>;
                                                prf = <{PRF}>;
                                                antd = <{ANTD}>;
                                                power = <{POWER}>;
                                        }};
'''.format(**dtree['CALIB'][key])
    
    str += '''
                               }};
                        }};
                }};
        }};

        __overrides__ {{
                dw1000_eui = <&dw1000>,"decawave,eui64#0";
                dw1000_profile = <&dw1000>,"decawave,default";
        }};
}};
'''.format(**dtree)

    return str
           


def main():

    parser = argparse.ArgumentParser(description="EEPROM DT decompiler")

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('file', type=str, nargs='?', default=None, help="File name")
    
    args = parser.parse_args()

    DT = read_dtree()

    if args.file is not None:
        name = args.file
    else:
        name = DT['EUI64']

    DTS = prepare_dtree(DT)

    with open(name + '.dts', 'w') as f:
        f.write(DTS)


if __name__ == "__main__": main()

