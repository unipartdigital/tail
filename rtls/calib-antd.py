#!/usr/bin/python3
#
# DW1000 Antenna delay calibration tool
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
from tail import eprint, eprints

from config import *


DISTANCES = {
    '70b3d5b1e0000014':  5.135,    # BSS1
    '70b3d5b1e0000015':  5.448,    # BSS2
    '70b3d5b1e0000016':  5.450,    # BSS3
    '70b3d5b1e0000017':  5.165,    # BSS4
    '70b3d5b1e0000011':  3.380,    # BSS5
    '70b3d5b1e0000013':  3.630,    # BSS6
    '70b3d5b1e0000018':  3.635,    # BSS7
    '70b3d5b1e0000019':  3.585,    # BSS8
}


class Config():

    blink_count  = 100
    blink_delay  = 0.010
    blink_wait   = 0.250

CFG = Config()

VERBOSE = 0
DEBUG = 0


def DECA_TWR(blk, tmr, remote, delay, rawts=False):

    adr1 = remote[0].addr
    adr2 = remote[1].addr
    eui1 = remote[0].eui
    eui2 = remote[1].eui

    Tm = tmr.sync()
    
    i1 = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay[0])
    
    i2 = blk.Blink(adr2,Tm)
    Tm = tmr.nap(delay[1])
    
    i3 = blk.Blink(adr1,Tm)
    
    blk.WaitBlinks((i1,i2,i3),remote,delay[2])
    
    T1 = blk.getTS(i1, eui1, rawts)
    T2 = blk.getTS(i1, eui2, rawts)
    T3 = blk.getTS(i2, eui2, rawts)
    T4 = blk.getTS(i2, eui1, rawts)
    T5 = blk.getTS(i3, eui1, rawts)
    T6 = blk.getTS(i3, eui2, rawts)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    
    if rawts:
        Dof = Tof / DW1000_CLOCK_GHZ
    else:
        Dof = Tof / (1<<32)
        
    Lof = Dof * C_AIR * 1E-9
        
    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Lof,Dof)


def ANTD_CAL(blk, tmr, tx, rxs, delay, count=100, rawts=False):
    errors = []
    for rx in rxs:
        if rx.eui in DISTANCES:
            if VERBOSE > 1:
                eprints('    {} to {} >>> '.format(tx.host,rx.host))
            delays = [ ]
            for i in range(count):
                if VERBOSE > 1 and i%10 == 0:
                    eprints('.')
                try:
                    (Lof,Dof) = DECA_TWR(blk, tmr, (tx,rx), delay, rawts=rawts)
                    if Lof > 0 and Lof < 100:
                        delays.append(Dof)
                    else:
                        if VERBOSE > 1:
                            eprints('*')
                except (ValueError,KeyError,TimeoutError):
                    if VERBOSE > 1:
                        eprints('?')
                        
            Davg = np.mean(delays)
            Dvar = np.var(delays)
            Dstd = math.sqrt(Dvar)
            Dmed = np.median(delays)
        
            Lavg = Davg * C_AIR * 1E-9
            Lstd = Dstd * C_AIR * 1E-9
            Lmed = Dmed * C_AIR * 1E-9

            Err = Lmed - DISTANCES[rx.eui]
            
            errors.append(Err)
            
            if VERBOSE > 1:
                eprint(' >> distance: {:.3f}m {:.3f}m error: {:.3f}m'.format(Lavg,Lstd,Err))

    Eavg = np.mean(errors)
    Evar = np.var(errors)
    Estd = np.sqrt(Evar)

    if VERBOSE > 0:
        eprint('    mean error: {:.3f}m {:.3f}m'.format(Eavg,Estd))
        
    return (Eavg,Estd)


def main():
    
    global VERBOSE
    
    parser = argparse.ArgumentParser(description="RTLS server")

    DW1000.AddParserArguments(parser)

    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count, help='Number of blinks')
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay, help='Delay between blinks')
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait, help='Time to wait timestamp reception')
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT, help='UDP port')

    parser.add_argument('-R', '--raw', action='store_true', default=False, help='Use raw timestamps')
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    VERBOSE = args.verbose
    DEBUG = args.debug
    
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
    
    for rem in remotes:
        for attr in DW1000_CALIB_CONFIG:
            rem.SetAttr(attr, DW1000_CALIB_CONFIG[attr])
    
    DW1000.HandleArguments(args,remotes)

    if VERBOSE > 2:
        DW1000.PrintAllRemoteAttrs(remotes)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc, args.debug)

    try:
        for tx in xmitters:
            if VERBOSE > 0:
                eprint('Calibrating {} <{}>'.format(tx.host,tx.eui))

            (Eavg,Estd) = ANTD_CAL(blk, tmr, tx, rceivers, (args.delay,args.delay,args.wait), count=args.count, rawts=args.raw)

            antd = int(tx.GetAttr('antd'),0)
            corr = int((Eavg/C_AIR) * DW1000_CLOCK_GHZ)
            antd += corr
            
            tx.SetAttr('antd', antd)
            antd = tx.GetAttr('antd')
            
            if VERBOSE > 0:
                eprint('    correction: {:+2d}'.format(corr))
                eprint('FINAL VALUE:')

            print(antd)
            
    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    

if __name__ == "__main__":
    main()

