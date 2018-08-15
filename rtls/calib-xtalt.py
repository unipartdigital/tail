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

    rawts        = True
    
    blink_count  = 100
    blink_delay  = 0.010
    blink_wait   = 0.010

CFG = Config()

VERBOSE = 0


def xtalt_ppm(blk, tx, rxs, tmr):
    
    tm = tmr.get()
            
    i1 = blk.Blink(tx.addr,tm)
    tm = tmr.nap(CFG.blink_delay)
    
    i2 = blk.Blink(tx.addr,tm)
    tm = tmr.nap(CFG.blink_wait)
    
    Fcnt = 0.0
    Fsum = 0.0
    
    if VERBOSE > 2:
        eprint('BLINK @{}'.format(tx.eui))

    for rx in rxs:
        try:
            T1 = blk.getTS(i1, tx.eui, CFG.rawts)
            T2 = blk.getTS(i1, rx.eui, CFG.rawts)
            T3 = blk.getTS(i2, tx.eui, CFG.rawts)
            T4 = blk.getTS(i2, rx.eui, CFG.rawts)
            
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

            if VERBOSE > 2:
                eprint('    {}: {:7.3f}ppm {:7.3f}ppm {:6.1f}dBm'.format(rx.eui,Err*1E6,Est*1E6,Pwr))
                
        except (ValueError,KeyError):
            if VERBOSE > 2:
                eprint('    {}:   ?'.format(rx.eui))

    if Fcnt > 0:
        Fppm = Fsum/Fcnt
    else:
        Fppm = None
    
    return Fppm


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
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    VERBOSE = args.verbose
    
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

    if VERBOSE > 1:
        DW1000.PrintAllRemoteAttrs(remotes)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc, args.debug)

    try:
        
        for tx in xmitters:
            if VERBOSE > 0:
                eprint('Calibrating {} <{}>'.format(tx.host,tx.eui))
            xtalt = int(tx.GetAttr('xtalt'))
            while True:
                Pcnt = 0
                Psum = 0
                tx.SetAttr('xtalt', xtalt)
                for i in range(CFG.blink_count):
                    Fppm = xtalt_ppm(blk,tx,rceivers,tmr)
                    if Fppm is not None:
                        Pcnt += 1
                        Psum += Fppm
                if Pcnt > 0:
                    Pavg = Psum/Pcnt * 1E6
                    if VERBOSE > 0:
                        eprint('    XTALT:{} {:.3f}ppm'.format(xtalt,Pavg))
                    if Pavg > 8.0:
                        xtalt -= int(Pavg/4)
                    elif Pavg > 1.8:
                        xtalt -= 1
                    elif Pavg < -8.0:
                        xtalt -= int(Pavg/4)
                    elif Pavg < -1.8:
                        xtalt += 1
                    else:
                        break
                else:
                    break

            if VERBOSE > 0:
                eprint('Calibration for {}:'.format(tx.host))
            
            print(xtalt)
        
    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    

if __name__ == "__main__":
    main()

