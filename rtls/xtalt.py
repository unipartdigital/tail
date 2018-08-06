#!/usr/bin/python3
#
# Xtal Trim analysis for Tail algorithm development
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
    blink_wait   = 0.050

CFG = Config()

VERBOSE = 0


def main():
    
    global VERBOSE
    
    parser = argparse.ArgumentParser(description="RTLS server")

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

    DEBUG = args.debug
    VERBOSE = args.verbose
    
    rawts = args.raw

    blink_count = args.count
    blink_delay = args.delay
    blink_wait = args.wait

    rpc = tail.RPC(('', args.port))
    
    remotes = [ ]
    xmiters = [ ]
    recvers = [ ]
    
    for host in args.remote:
        try:
            xmit = host.startswith('*') or host.endswith('*')
            host = host.strip('*').rstrip('*')
            anchor = DW1000(host,args.port,rpc)
            remotes.append(anchor)
            if xmit:
                xmiters.append(anchor)
            else:
                recvers.append(anchor)
        except:
            eprint('Remote {} exist does not'.format(host))

    DW1000.HandleArguments(args,remotes)

    if VERBOSE > 0:
        DW1000.PrintAllRemoteAttrs(remotes)

    tmr = tail.Timer()

    blk = tail.Blinker(rpc)
    blk.DEBUG = DEBUG
    
    tx = xmiters[0]
        
    Tcnt = 0
    Tsum = 0
    
    eprint('Blinker starting')

    try:
        for i in range(blink_count):
            
            tm = tmr.nap(blink_wait)
            
            i1 = blk.Blink(tx.addr,tm)
            tm = tmr.nap(blink_delay)
            
            i2 = blk.Blink(tx.addr,tm)
            tm = tmr.nap(blink_delay)

            Fcnt = 0.0
            Fsum = 0.0

            if VERBOSE > 0:
                print('BLINK @{}'.format(tx.eui))

            for rx in recvers:
                
                try:
                    T1 = blk.getTS(i1, tx.eui, rawts)
                    T2 = blk.getTS(i1, rx.eui, rawts)
                    T3 = blk.getTS(i2, tx.eui, rawts)
                    T4 = blk.getTS(i2, rx.eui, rawts)
                    
                    F2 = blk.getXtalPPM(i1, rx.eui)
                    F4 = blk.getXtalPPM(i2, rx.eui)
                    
                    P2 = blk.getRFPower(i1, rx.eui)
                    P4 = blk.getRFPower(i2, rx.eui)
                    
                    T31 = T3 - T1
                    T42 = T4 - T2

                    Pwr = P2
                    Est = (F2 + F4) / 2
                    Err = (T42 - T31) / T42

                    Fcnt += 1
                    Fsum += Err

                    if VERBOSE > 0:
                        print('    {}: {:7.3f}ppm {:7.3f}ppm {:6.1f}dBm'.format(rx.eui,Err*1E6,Est*1E6,Pwr))
                
                except (ValueError,KeyError):
                    if VERBOSE > 0:
                        print('    {}:   ?'.format(rx.eui))

            if Fcnt > 0:
                Fppm = Fsum/Fcnt
                Tcnt += 1.0
                Tsum += Fppm

                if VERBOSE > 0:
                    print('             AVERAGE: {:7.3f}ppm'.format(Fppm*1E6))
                    print()

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    if Tcnt > 0:
        Tavg = Tsum/Tcnt
        print()
        print('FINAL STATISTICS:')
        print('  Samples:  {}'.format(Tcnt))
        print('  Average:  {:.3f}ppm'.format(Tavg*1E6))
        
    eprint('\nDone')
    

if __name__ == "__main__":
    main()

