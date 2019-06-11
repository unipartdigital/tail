#!/usr/bin/python3
#
# XTAL speed sync against NTP
#
# Usage:  ntpsync.py xmit* recv1 recv2 recv3 ... [usual args]
#

import sys
import math
import queue
import socket
import json
import pprint
import argparse
import threading
import tail

import numpy as np
import numpy.linalg as lin

from numpy import dot

from tail import *
from config import *
from pprint import pprint


class Config():

    blink_count    = 1000000
    blink_delay    = 0.100
    blink_wait     = 1.0
    blink_interval = 60

CFG = Config()

DATA = {}
    

def XTAL_PPM(blk, tmr, tx, rxs, devs, INDEX=0, START=0, CH=7, PRF=64, rawts=False):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32

    veprint(1,'\n** BLINK {}\n'.format(INDEX))

    tm = tmr.sync()
    i1 = blk.Blink(tx,tm)
    tm = tmr.nap(CFG.blink_delay)
    i2 = blk.Blink(tx,tm)

    blk.WaitBlinks((i1,i2),devs,CFG.blink_wait)
        
    Fcnt = 0
    Fsum = 0.0
    Esum = 0.0
    Psum = 0.0
    Rsum = 0.0
    Tsum = 0.0
    
    DATA[INDEX] = {}
    
    veprint(1,'    ANCHOR          Etx        Erx        Ediff      Ebk        Ehw        Pwr')
    veprint(1,'    ===============================================================================')
    
    for rx in rxs:
        try:
            key = rx.host

            T1 = blk.getTS(i1, tx.eui, rawts)
            T2 = blk.getTS(i1, rx.eui, rawts)
            T3 = blk.getTS(i2, tx.eui, rawts)
            T4 = blk.getTS(i2, rx.eui, rawts)

            S2 = blk.getTSW(i1, rx.eui)
            
            F2 = blk.getXtalPPM(i1, rx.eui)
            F4 = blk.getXtalPPM(i2, rx.eui)
            
            P2 = blk.getRxPower(i1, rx.eui)
            P4 = blk.getRxPower(i2, rx.eui)

            P24 = (P2 + P4) / 2
            F24 = (F2 + F4) / 2
            
            T31 = T3 - T1
            T42 = T4 - T2
            
            Err = (T42 - T31) / T42
            Pwr = DW1000.RxPower2dBm(P24,PRF)
            
            Fcnt += 1
            Esum += Err
            Fsum += F24
            Psum += P24

            DATA[INDEX][key] = {}
            DATA[INDEX][key]['HWTx'] = T1
            DATA[INDEX][key]['HWRx'] = T2
            DATA[INDEX][key]['SWRx'] = S2
            DATA[INDEX][key]['Err'] = Err
            DATA[INDEX][key]['Pwr'] = Pwr

            T0 = DATA[START][key]['HWTx']
            T10 = T1 - T0
            
            R0 = DATA[START][key]['HWRx']
            R20 = T2 - R0
            
            S0 = DATA[START][key]['SWRx']
            S20 = S2 - S0
            
            if S20 > 0:
                ErrRxNtp = (R20 - S20) / S20
                ErrTxNtp = (T10 - S20) / S20
            else:
                ErrRxNtp = 0.0
                ErrTxNtp = 0.0
            
            Rsum += ErrRxNtp
            Tsum += ErrTxNtp

            veprint(1, '    {:<12s}  {:7.3f}ppm {:7.3f}ppm {:7.3f}ppm {:7.3f}ppm {:7.3f}ppm {:6.1f}dBm'.format(rx.host, ErrTxNtp*1E6, ErrRxNtp*1E6, (ErrRxNtp-ErrTxNtp)*1E6, Err*1E6, F24*1E6, Pwr))
                
        except (ValueError,KeyError):
            veprint(1,'    {:<12s}'.format(rx.host))

    Eavg = Esum/Fcnt * 1E6
    Favg = Fsum/Fcnt * 1E6
    Ravg = Rsum/Fcnt * 1E6
    Tavg = Tsum/Fcnt * 1E6
    
    Pavg = Psum/Fcnt
    Pwr  = DW1000.RxPower2dBm(Pavg,PRF)
                
    veprint(1,'    ===============================================================================')
    veprint(1,'    AVERAGE       {:7.3f}ppm {:7.3f}ppm {:7.3f}ppm {:7.3f}ppm {:7.3f}ppm {:6.1f}dBm'.format(Tavg, Ravg, (Ravg-Tavg), Eavg, Favg, Pwr))
        
    return


def main():
    
    parser = argparse.ArgumentParser(description="XTAL NTP test")

    DW1000.AddParserArguments(parser)

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-i', '--interval', type=float, default=CFG.blink_interval)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    tail.VERBOSE = args.verbose
    
    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait = args.wait
    CFG.blink_interval = args.interval
    
    rpc = tail.RPC(('', args.port))
    
    remotes  = [ ]
    xmitters = [ ]
    rceivers = [ ]
    
    for host in args.remote:
        try:
            xmit = host.startswith('*') or host.endswith('*')
            host = host.strip('*').rstrip('*')
            anchor = DW1000(host,args.port,rpc)
            remotes.append(anchor)
            if xmit:
                xmitters.append(anchor)
            else:
                rceivers.append(anchor)
        except:
            eprint('Remote {} not available'.format(host))

    DW1000.HandleArguments(args,remotes)

    if tail.VERBOSE > 0:
        DW1000.PrintAllRemoteAttrs(remotes,True)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc, args.debug)
    
    ch  = int(xmitters[0].GetDWAttr('channel'))
    prf = int(xmitters[0].GetDWAttr('prf'))
    
    DATA = {}
    
    try:
        for i in range(CFG.blink_count):
            try:
                XTAL_PPM(blk, tmr, xmitters[0], rceivers, remotes, INDEX=i, START=0, CH=ch, PRF=prf)
                tmr.nap(CFG.blink_interval)
                
            except (TimeoutError,ValueError,KeyError):
                eprint('Error. Continuing...')

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()


if __name__ == "__main__":
    main()

