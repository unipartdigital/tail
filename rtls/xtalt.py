#!/usr/bin/python3
#
# Xtal Trim analysis for Tail algorithm development
#
# Usage:  xtalt.py xmit* recv1 recv2 recv3 ... [usual args]
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

from tail import DW1000
from tail import eprint

from config import *


class Config():

    blink_count  = 100
    blink_delay  = 0.010
    blink_wait   = 0.100

CFG = Config()

VERBOSE = 0


def XTAL_PPM(blk, tmr, tx, rxs, rawts=True, CH=7, PRF=64):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32

    if VERBOSE > 1:
        print('BLINK {} <{}>'.format(tx.host,tx.eui))

    tm = tmr.sync()
    i1 = blk.Blink(tx,tm)
    tm = tmr.nap(CFG.blink_delay)
    i2 = blk.Blink(tx,tm)

    try:
        blk.WaitBlinks((i1,i2),rxs,CFG.blink_wait)
        
    except (TimeoutError):
        pass
        
    Fcnt = 0
    Fsum = 0.0
    Esum = 0.0
    Psum = 0.0
    
    for rx in rxs:
        try:
            T1 = blk.getTS(i1, tx.eui, rawts)
            T2 = blk.getTS(i1, rx.eui, rawts)
            T3 = blk.getTS(i2, tx.eui, rawts)
            T4 = blk.getTS(i2, rx.eui, rawts)
            
            F2 = blk.getXtalPPM(i1, rx.eui)
            F4 = blk.getXtalPPM(i2, rx.eui)
            
            P2 = blk.getRxPower(i1, rx.eui)
            P4 = blk.getRxPower(i2, rx.eui)

            P24 = (P2+P4)/2
            
            T31 = T3 - T1
            T42 = T4 - T2
            
            Pwr = DW1000.RxPower2dBm(P24,PRF)
            Est = (F2 + F4) / 2
            Err = (T42 - T31) / T42
            
            Fcnt += 1
            Fsum += Err
            Esum += Est
            Psum += P24

            Pwr = DW1000.RxPower2dBm(P24,PRF)
            
            if VERBOSE > 1:
                print('    {:<8s} <{:s}>   {:7.3f}ppm {:7.3f}ppm {:6.1f}dBm'.format(rx.host,rx.eui,Err*1E6,Est*1E6,Pwr))
                
        except (ValueError,KeyError):
            if VERBOSE > 1:
                print('    {:<8s} <{:s}>'.format(rx.host,rx.eui))

    Favg = Fsum/Fcnt
    Eavg = Esum/Fcnt
    Pavg = Psum/Fcnt
    
    return (Favg,Eavg,Pavg,Fcnt)


def main():
    
    global VERBOSE
    
    parser = argparse.ArgumentParser(description="XTALT test")

    DW1000.AddParserArguments(parser)

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-R', '--raw', action='store_true', default=False)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    VERBOSE = args.verbose
    
    CFG.rawts = args.raw

    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait = args.wait

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
            eprint('Remote {} exist does not'.format(host))

    DW1000.HandleArguments(args,remotes)

    if VERBOSE > 0:
        DW1000.PrintAllRemoteAttrs(remotes)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc, args.debug)
    
    ch  = int(xmitters[0].GetDWAttr('channel'))
    prf = int(xmitters[0].GetDWAttr('prf'))
    
    Scnt = 0
    Bcnt = 0
    Fsum = 0.0
    Esum = 0.0
    Psum = 0.0
    
    eprint('Blinker starting')

    try:
        for i in range(CFG.blink_count):

            try:
                (Favg,Eavg,Pavg,Fcnt) = XTAL_PPM(blk, tmr, xmitters[0], rceivers, rawts=args.raw, CH=ch, PRF=prf)

                Bcnt += 1
                Scnt += Fcnt
                Fsum += Favg*Fcnt
                Esum += Eavg*Fcnt
                Psum += Pavg*Fcnt

                Pwr = DW1000.RxPower2dBm(Pavg,prf)
                
                if VERBOSE > 1:
                    print('    ==================================================================')
                    print('    AVERAGE                           {:7.3f}ppm {:7.3f}ppm {:6.1f}dBm'.format(Favg*1E6,Eavg*1E6,Pwr))
                    print()

            except (ValueError,KeyError,ZeroDivisionError):
                pass
                    
    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    if Scnt > 0:
        
        Favg = Fsum/Scnt
        Eavg = Esum/Scnt
        Pavg = Psum/Scnt
        
        Pwr = DW1000.RxPower2dBm(Pavg,prf)
                
        print()
        print('FINAL STATISTICS:')
        print('  Blinks:   {}'.format(Bcnt))
        print('  Samples:  {}'.format(Scnt))
        print('  XTALT:    {:.3f}ppm'.format(Favg*1E6))
        print('  XEST:     {:.3f}ppm'.format(Eavg*1E6))
        print('  POWER:    {:.1f}dBm'.format(Pwr))
        

if __name__ == "__main__":
    main()

