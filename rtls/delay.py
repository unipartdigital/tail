#!/usr/bin/python3
#
# Anchor distance tool for Tail algorithm development
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
    blink_wait   = 0.250

    rawts        = 0
    ewma         = 32

    algo         = 'DECA'

CFG = Config()

VERBOSE = 0


def DECA_TWR(anc1, anc2, delay1, delay2, blk, tmr):

    adr1 = anc1.addr
    adr2 = anc2.addr

    eui1 = anc1.eui
    eui2 = anc2.eui

    Tm = tmr.sync()
    
    i1 = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay1)
    
    i2 = blk.Blink(adr2,Tm)
    Tm = tmr.nap(delay1)
    
    i3 = blk.Blink(adr1,Tm)
    
    blk.WaitBlinks((i1,i2,i3),(anc1,anc2),delay2)
    
    T1 = blk.getTS(i1, eui1, CFG.rawts)
    T2 = blk.getTS(i1, eui2, CFG.rawts)
    T3 = blk.getTS(i2, eui2, CFG.rawts)
    T4 = blk.getTS(i2, eui1, CFG.rawts)
    T5 = blk.getTS(i3, eui1, CFG.rawts)
    T6 = blk.getTS(i3, eui2, CFG.rawts)
    
    F2 = blk.getXtalPPM(i1, eui2)
    F6 = blk.getXtalPPM(i3, eui2)

    P2 = blk.getRFPower(i1, eui2)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    
    if CFG.rawts:
        Dof = Tof / DW_CLOCK_GHZ
        Rtt = T41 / DW_CLOCK_GHZ
    else:
        Dof = Tof / (1<<32)
        Rtt = T41 / (1<<32)
        
    Lof = Dof * C_AIR * 1E-9
        
    Est = (F2 + F6) / 2
    Err = (T62 - T51) / T62
    
    Pwr = P2
    
    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Lof,Dof,Rtt,Err,Est,Pwr)

            
def DECA_FAST_TWR(anc1, anc2, delay1, delay2, blk, tmr):
    
    adr1 = anc1.addr
    adr2 = anc2.addr

    eui1 = anc1.eui
    eui2 = anc2.eui

    Tm = tmr.sync()

    i1 = blk.GetBlinkId(Tm)
    i2 = blk.GetBlinkId(Tm)
    i3 = blk.GetBlinkId(Tm)

    blk.TriggerBlink(adr2,i1,i2)
    blk.TriggerBlink(adr1,i2,i3)
    
    tmr.nap(delay1)
    
    blk.BlinkID(adr1,i1)
    
    blk.WaitBlinks((i1,i2,i3),(anc1,anc2),delay2)
    
    T1 = blk.getTS(i1, eui1, CFG.rawts)
    T2 = blk.getTS(i1, eui2, CFG.rawts)
    T3 = blk.getTS(i2, eui2, CFG.rawts)
    T4 = blk.getTS(i2, eui1, CFG.rawts)
    T5 = blk.getTS(i3, eui1, CFG.rawts)
    T6 = blk.getTS(i3, eui2, CFG.rawts)
    
    F2 = blk.getXtalPPM(i1, eui2)
    F6 = blk.getXtalPPM(i3, eui2)

    P2 = blk.getRFPower(i1, eui2)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    
    if CFG.rawts:
        Dof = Tof / DW_CLOCK_GHZ
        Rtt = T41 / DW_CLOCK_GHZ
    else:
        Dof = Tof / (1<<32)
        Rtt = T41 / (1<<32)
        
    Lof = Dof * C_AIR * 1E-9
        
    Est = (F2 + F6) / 2
    Err = (T62 - T51) / T62
    
    Pwr = P2

    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Lof,Dof,Rtt,Err,Est,Pwr)

            
def main():
    
    global VERBOSE, CFG
    
    parser = argparse.ArgumentParser(description="RTLS server")

    DW1000.AddParserArguments(parser)
    
    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-E', '--ewma', type=int, default=CFG.ewma)
    parser.add_argument('-A', '--algo', type=str, default=CFG.algo)
    parser.add_argument('-R', '--raw', action='store_true', default=False)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    VERBOSE = args.verbose

    if args.algo == 'FAST':
        algo = DECA_FAST_TWR
    else:
        algo = DECA_TWR
        
    CFG.algo = args.algo
    CFG.ewma = args.ewma
    CFG.rawts = args.raw
    
    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait = args.wait

    rpc = tail.RPC(('', args.port))

    remotes = [ ]
    for host in args.remote:
        try:
            anchor = DW1000(host,args.port,rpc)
            remotes.append(anchor)
        except:
            eprint('Remote {} exist does not'.format(host))

    DW1000.HandleArguments(args,remotes)
    
    if VERBOSE > 0:
        DW1000.PrintAllRemoteAttrs(remotes)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc, args.debug)

    Tcnt = 0
    Dsum = 0.0
    Dsqr = 0.0
    Rsum = 0.0
    Lfil = 0.0
    Lvar = 0.0

    eprint('Blinker starting')

    try:
        for i in range(CFG.blink_count):
            try:
                (Lof,Dof,Rtt,Err,Est,Pwr) = algo(remotes[0], remotes[1], CFG.blink_delay, CFG.blink_wait, blk, tmr)
                if Lof > 0 and Lof < 100:
                    Tcnt += 1
                    Dsum += Dof
                    Dsqr += Dof*Dof
                    Rsum += Rtt
                    if VERBOSE > 0:
                        Ldif = Lof - Lfil
                        Lvar += (Ldif*Ldif - Lvar) / CFG.ewma
                        if Tcnt < CFG.ewma:
                            Lfil += Ldif / Tcnt
                        else:
                            Lfil += Ldif / CFG.ewma
                        print('{:.3f}m {:.3f}m -- Dist:{:.3f}m ToF:{:.3f}ns Xerr:{:.3f}ppm Xest:{:.3f}ppm Rx:{:.1f}dBm Rtt:{:.3f}ms'.format(Lfil,math.sqrt(Lvar),Lof,Dof,Err*1E6,Est*1E6,Pwr,Rtt*1E-6))
                else:
                    if VERBOSE > 0:
                        eprint('*')
                    else:
                        eprint(end='*', flush=True)
            except (ValueError,KeyError,TimeoutError):
                if VERBOSE > 0:
                    eprint('?')
                else:
                    eprint(end='?', flush=True)
            if VERBOSE == 0 and i%10 == 0:
                eprint(end='.', flush=True)
            
    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    if Tcnt > 0:
        Davg = Dsum/Tcnt
        Dvar = Dsqr/Tcnt - Davg*Davg
        Dstd = math.sqrt(Dvar)
        Lavg = Davg * C_AIR * 1E-9
        Lstd = Dstd * C_AIR * 1E-9
        Ravg = Rsum/Tcnt * 1E-6
        print()
        print('FINAL STATISTICS:')
        print('  Samples:  {}'.format(Tcnt))
        print('  Average:  {:.3f}m {:.3f}ns'.format(Lavg,Davg))
        print('  Std.Dev:  {:.3f}m {:.3f}ns'.format(Lstd,Dstd))
        print('  RTT.Avg:  {:.3f}ms'.format(Ravg))

    else:
        print()
        print('NO SUITABLE SAMPLES')


if __name__ == "__main__":
    main()

