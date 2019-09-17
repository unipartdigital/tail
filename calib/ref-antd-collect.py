#!/usr/bin/python3
#
# Collect antd calibration data for reference anchors.
#
# Usage: ref-antd-collect <DWARG..>
#		<-D|--debug> <-v|--verbose>
#		<-n|--count> <-d|--delay> <-w|--wait>
#		<-f|--file> <-L|--distance>
#		host1:host2 <host3:host4...>
#
# Run TWR between host:host pairs for <count> times.
# Record average KPIs for every pair, and save into <file>
# 
# This information is then fed into ref-antd-calc, which
# solves the LSE solution for ANTDs. 
# 


import sys
import math
import queue
import socket
import json
import argparse
import threading
import tail

import numpy as np
import numpy.linalg as lin

from tail import *
from config import *

from tail import eprint, eprints


class CFG():

    blink_count  = 100
    blink_delay  = 0.010
    blink_wait   = 0.100

    distance     = None
    
    ch           = None
    prf          = None
    freq         = None


Pi = math.pi
Cs = 299792458

UWB_Ch = ( None, 3494.4E6, 3993.6E6, 4492.8E6, 3993.6E6, 6489.6E6, None, 6489.6E6 )


##
## Functions
##

def TWR_EST(blk, tmr, dut, rem, delay, rawts=True):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32

    Tm = tmr.sync()
    i1 = blk.Blink(dut,Tm)
    Tm = tmr.nap(delay[0])
    i2 = blk.Blink(rem,Tm)
    Tm = tmr.nap(delay[1])
    i3 = blk.Blink(dut,Tm)

    blk.WaitBlinks((i1,i2,i3),(dut,rem),delay[2])
    
    T1 = blk.getTS(i1, dut.eui, rawts)
    T2 = blk.getTS(i1, rem.eui, rawts)
    T3 = blk.getTS(i2, rem.eui, rawts)
    T4 = blk.getTS(i2, dut.eui, rawts)
    T5 = blk.getTS(i3, dut.eui, rawts)
    T6 = blk.getTS(i3, rem.eui, rawts)
    
    P1 = blk.getRxPower(i2,dut.eui)
    P2 = blk.getRxPower(i1,rem.eui)
    
    F1 = blk.getFpPower(i2,dut.eui)
    F2 = blk.getFpPower(i1,rem.eui)

    C1 = blk.getTemp(i1,dut.eui)
    C2 = blk.getTemp(i2,rem.eui)
    
    V1 = blk.getVolt(i1,dut.eui)
    V2 = blk.getVolt(i2,rem.eui)
    
    S1 = blk.getSNR(i2,dut.eui)
    S2 = blk.getSNR(i1,rem.eui)
    
    N1 = blk.getNoise(i2,dut.eui)
    N2 = blk.getNoise(i1,rem.eui)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    PPM = 1E6 * (T62 - T51) / T62

    Tof = (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / SCL
    Lof = Dof * Cs * 1E-9
    
    if Lof < 0 or Lof > 100:
        raise ValueError
    
    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Dof,Lof,PPM,S1,P1,F1,N1,C1,V1,S2,P2,F2,N2,C2,V2)


def TWR_RUN(blk, tmr, rems, devs, delay, count):

    RES = {}

    for (rem1,rem2) in rems:
        
        key = rem1.host + '::' + rem2.host
        
        DATA = {}
        
        DATA['Dist'] = []
        DATA['PPM']  = []
        DATA['PWR1'] = []
        DATA['PWR2'] = []
        DATA['FPR1'] = []
        DATA['FPR2'] = []
        DATA['Temp1'] = []
        DATA['Temp2'] = []
        DATA['Volt1'] = []
        DATA['Volt2'] = []
    
        for i in range(count):
            try:
                #  0   1   2   3  4  5  6  7  8  9  10 11 12 13 14
                # (Dof,Lof,PPM,S1,P1,F1,N1,C1,V1,S2,P2,F2,N2,C2,V2) =
                X = TWR_EST(blk,tmr,rem1,rem2,delay)

                if CFG.distance is not None:
                    if X[1] < 0.95 * CFG.distance or X[1] > 1.05 * CFG.distance:
                        raise ValueError('Distance out of range')

                DATA['Dist'].append(X[1])
                DATA['PPM'].append(X[2])
                DATA['PWR1'].append(X[4])
                DATA['PWR2'].append(X[10])
                DATA['FPR1'].append(X[5])
                DATA['FPR2'].append(X[11])
                DATA['Temp1'].append(X[7])
                DATA['Temp2'].append(X[13])
                DATA['Volt1'].append(X[8])
                DATA['Volt2'].append(X[14])
                    
            except (TimeoutError):
                #eprint('T {} <> {}'.format(dut.host,rem.host))
                eprints('T')
            except (KeyError):
                eprints('?')
            except (ValueError):
                eprints('*')
            except (ZeroDivisionError):
                eprints('0')
                
            if i%10 == 0:
                eprints('.')

        RES[key] = {}

        pwr = np.mean(DATA['PWR1'])
        std = np.std(DATA['PWR1'])
        pavg1 = DW1000.RxPower2dBm(pwr,CFG.prf)
        pstd1 = DW1000.RxPower2dBm(pwr+std,CFG.prf) - pavg1
        
        pwr = np.mean(DATA['PWR2'])
        std = np.std(DATA['PWR2'])
        pavg2 = DW1000.RxPower2dBm(pwr,CFG.prf)
        pstd2 = DW1000.RxPower2dBm(pwr+std,CFG.prf) - pavg2
        
        pwr = np.mean(DATA['FPR1'])
        std = np.std(DATA['FPR1'])
        favg1 = DW1000.RxPower2dBm(pwr,CFG.prf)
        fstd1 = DW1000.RxPower2dBm(pwr+std,CFG.prf) - favg1
        
        pwr = np.mean(DATA['FPR2'])
        std = np.std(DATA['FPR2'])
        favg2 = DW1000.RxPower2dBm(pwr,CFG.prf)
        fstd2 = DW1000.RxPower2dBm(pwr+std,CFG.prf) - favg2
        
        RES[key]['Dist.avg'] = np.mean(DATA['Dist'])
        RES[key]['Dist.std'] = np.std(DATA['Dist'])
        RES[key]['PPM.avg'] = np.mean(DATA['PPM'])
        RES[key]['PPM.std'] = np.std(DATA['PPM'])
        
        RES[key]['Temp1.avg'] = np.mean(DATA['Temp1'])
        RES[key]['Temp1.std'] = np.std(DATA['Temp1'])
        RES[key]['Volt1.avg'] = np.mean(DATA['Volt1'])
        RES[key]['Volt1.std'] = np.std(DATA['Volt1'])
        
        RES[key]['Temp2.avg'] = np.mean(DATA['Temp2'])
        RES[key]['Temp2.std'] = np.std(DATA['Temp2'])
        RES[key]['Volt2.avg'] = np.mean(DATA['Volt2'])
        RES[key]['Volt2.std'] = np.std(DATA['Volt2'])
        
        RES[key]['PWR1.avg'] = pavg1
        RES[key]['PWR1.std'] = pstd1
        RES[key]['PWR2.avg'] = pavg2
        RES[key]['PWR2.std'] = pstd2
        RES[key]['FPR1.avg'] = favg1
        RES[key]['FPR1.std'] = fstd1
        RES[key]['FPR2.avg'] = favg2
        RES[key]['FPR2.std'] = fstd2

        eprint()
    
    return RES


def main():
    
    global VERBOSE, CFG
    
    parser = argparse.ArgumentParser(description="DW1000 calibratuur")

    DW1000.AddParserArguments(parser)

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-f', '--file', type=str, default=None)
    parser.add_argument('-L', '--distance', type=float, default=None)
    
    parser.add_argument('remote', type=str, nargs='+', help="Remote pairs")
    
    args = parser.parse_args()
    
    tail.VERBOSE = args.verbose
    tail.DEBUG = args.debug

    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait  = args.wait

    CFG.distance = args.distance

    rpc = tail.RPC()
    
    hosts = { }
    devs = [ ]
    rems = [ ]
    
    for remotes in args.remote:
        (host1,host2) = remotes.split(':')
        try:
            if host1 not in hosts:
                hosts[host1] = DW1000(host1,args.port,rpc)
            if host2 not in hosts:
                hosts[host2] = DW1000(host2,args.port,rpc)
            devs.append(hosts[host1])
            devs.append(hosts[host2])
            rems.append((hosts[host1],hosts[host2]))
        except:
            eprint('Remotes {} not available'.format(remotes))
    
    DW1000.HandleArguments(args,devs)

    if tail.VERBOSE > 2:
        DW1000.PrintAllRemoteAttrs(devs,True)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc)

    CFG.ch = int(devs[0].GetDWAttr('channel'))
    CFG.prf = int(devs[0].GetDWAttr('prf'))
    CFG.freq = UWB_Ch[CFG.ch]
    
    delay = [ CFG.blink_delay, CFG.blink_delay, CFG.blink_wait ]

    if args.file is not None:
        fd = open(args.file, 'a')
    else:
        fd = None

    try:
        TWR = TWR_RUN(blk, tmr, rems, devs, delay, args.count)
        
        for (rem1,rem2) in rems:
            
            key = rem1.host + '::' + rem2.host
            res = TWR[key]
            
            msg  = '{},{}'.format(rem1.host,rem2.host)
            msg += ',{:.3f}'.format(res['Dist.avg'])
            msg += ',{:.3f}'.format(res['Dist.std'])
            msg += ',{:.3f}'.format(res['PPM.avg'])
            msg += ',{:.3f}'.format(res['PPM.std'])
            msg += ',{:.1f}'.format(res['Temp1.avg']) 
            msg += ',{:.1f}'.format(res['Temp2.avg'])
            msg += ',{:.3f}'.format(res['Volt1.avg']) 
            msg += ',{:.3f}'.format(res['Volt2.avg'])
            msg += ',{:.1f}'.format(res['PWR1.avg'])
            msg += ',{:.2f}'.format(res['PWR1.std'])
            msg += ',{:.1f}'.format(res['PWR2.avg'])
            msg += ',{:.2f}'.format(res['PWR2.std'])
            msg += ',{:.1f}'.format(res['FPR1.avg'])
            msg += ',{:.2f}'.format(res['FPR1.std'])
            msg += ',{:.1f}'.format(res['FPR2.avg'])
            msg += ',{:.2f}'.format(res['FPR2.std'])
            
            print(msg)
            
            if fd is not None:
                fd.write(msg + '\n')
                
    except (KeyboardInterrupt):
        eprint('\nStopping...')
    
    if fd is not None:
        fd.close()
        
    blk.stop()
    rpc.stop()



if __name__ == "__main__":
    main()

