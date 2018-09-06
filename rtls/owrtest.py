#!/usr/bin/python3
#
# One-Way Ranging tool for algorithm development
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
import matplotlib.pyplot as plot

from numpy import dot

from tail import DW1000
from tail import eprint, eprints

from config import *


class Config():

    blink_count  = 100
    blink_delay  = 0.010
    blink_wait   = 0.500

    range        = -3.000
    binsize      =  2 / DW1000_CLOCK_GHZ

CFG = Config()

VERBOSE = 0
DEBUG = 0

def dprint(*args, **kwargs):
    if DEBUG > 0:
        print(*args, file=sys.stderr, flush=True, **kwargs)


BSS_DIST = [
    [0.000, 8.395, 9.963, 5.385, 2.700, 6.200, 8.310, 6.170],
    [8.395, 0.000, 5.390, 9.980, 6.035, 2.630, 6.340, 8.550],
    [9.963, 5.390, 0.000, 8.390, 8.260, 6.215, 2.780, 6.390],
    [5.385, 9.980, 8.390, 0.000, 6.310, 8.390, 6.060, 2.480],
    [2.700, 6.035, 8.260, 6.310, 0.000, 3.418, 6.891, 5.955],
    [6.200, 2.630, 6.215, 8.390, 3.418, 0.000, 5.958, 7.130],
    [8.310, 6.340, 2.780, 6.060, 6.891, 5.958, 0.000, 3.800],
    [6.170, 8.550, 6.390, 2.480, 5.955, 7.130, 3.800, 0.000],
]


def GetDist(eui1,eui2):
    i = DW1000_DEVICE_CALIB[eui1]['bss']
    j = DW1000_DEVICE_CALIB[eui2]['bss']
    return BSS_DIST[i][j]

def GetDistJiffies(eui1,eui2,SCL):
    return int(round(GetDist(eui1,eui2)/C_AIR * SCL * 1E9))


def TDOF1(blk, tmr, remote, delay, rawts=False):

    #
    #     [1]           [2]             [3]
    #
    # (a) Ta1 -->--->-- Ta2 --<>---<>-- Ta3
    #                                       \__delay[0]
    #                                       /
    # (b)               Tb2 --->--->--- Tb3
    #
    
    adr1 = remote[0].addr
    adr2 = remote[1].addr
    adr3 = remote[2].addr
    eui1 = remote[0].eui
    eui2 = remote[1].eui
    eui3 = remote[2].eui

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32
        
    Tm = tmr.sync()
    
    ia = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay[0])
    ib = blk.Blink(adr2,Tm)
    
    blk.WaitBlinks((ia,ib),remote,delay[2])
    
    Ta2 = blk.getTS(ia, eui2, rawts)
    Ta3 = blk.getTS(ia, eui3, rawts)
    Tb2 = blk.getTS(ib, eui2, rawts)
    Tb3 = blk.getTS(ib, eui3, rawts)

    J12 = GetDistJiffies(eui1,eui2,SCL)
    J13 = GetDistJiffies(eui1,eui3,SCL)
    J23 = GetDistJiffies(eui2,eui3,SCL)
    
    Cdif = (Tb3 - Tb2) - J23
    dprint(' >>> Clock diff: {}'.format(Cdif))
    
    TDOA = (Ta3 - Cdif) - Ta2
    REAL = J13 - J12
    TDER = TDOA - REAL
    dprint(' >>> TDOA:{} REAL:{} ERROR:{}'.format(TDOA,REAL,TDER))

    Derr = TDER / SCL
    Lerr = Derr * C_AIR * 1E-9
    dprint(' >>> Error: {:.3f}ns {:.3f}m'.format(Derr,Lerr))

    blk.PurgeBlink(ia)
    blk.PurgeBlink(ib)
    
    return (Lerr,Derr,TDOA,REAL,TDER)


def TDOF2(blk, tmr, remote, delay, rawts=False):

    #
    #     [1]             [2]              [3]
    #
    # (a) Ta1 --->--->--- Ta2  --<>---<>-- Ta3
    #                                          \__delay[0]
    #                                          /
    # (b)                 Tb2  --->--->--- Tb3
    #                                          \__delay[1]
    #                                          /
    # (c)                 Tc2  --->--->--- Tc3
    #
    
    adr1 = remote[0].addr
    adr2 = remote[1].addr
    adr3 = remote[2].addr
    eui1 = remote[0].eui
    eui2 = remote[1].eui
    eui3 = remote[2].eui

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32
        
    Tm = tmr.sync()
    
    ia = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay[0])
    ib = blk.Blink(adr2,Tm)
    Tm = tmr.nap(delay[1])
    ic = blk.Blink(adr2,Tm)
    
    blk.WaitBlinks((ia,ib,ic),remote,delay[2])
    
    Ta2 = blk.getTS(ia, eui2, rawts)
    Ta3 = blk.getTS(ia, eui3, rawts)
    Tb2 = blk.getTS(ib, eui2, rawts)
    Tb3 = blk.getTS(ib, eui3, rawts)
    Tc2 = blk.getTS(ic, eui2, rawts)
    Tc3 = blk.getTS(ic, eui3, rawts)

    J12 = GetDistJiffies(eui1,eui2,SCL)
    J13 = GetDistJiffies(eui1,eui3,SCL)
    J23 = GetDistJiffies(eui2,eui3,SCL)

    Cdif = (Tb3 - Tb2) - J23
    dprint(' >>> Clock diff: {}'.format(Cdif))
    
    Dcb2 = Tc2 - Tb2
    Dcb3 = Tc3 - Tb3
    Drat = (Dcb3 - Dcb2) / (Dcb2 + Dcb3)
    dprint(' >>> Clock ratio: {:.3f}ppm'.format(Drat*1E6))
    
    TDOA = (Ta3 - Ta2) - Cdif + int((Tc3-Ta3)*Drat)
    REAL = J13 - J12
    TDER = TDOA - REAL
    dprint(' >>> TDOA:{} REAL:{} ERROR:{}'.format(TDOA,REAL,TDER))

    Derr = TDER / SCL
    Lerr = Derr * C_AIR * 1E-9
    dprint(' >>> Error: {:.3f}ns {:.3f}m'.format(Derr,Lerr))

    blk.PurgeBlink(ia)
    blk.PurgeBlink(ib)
    blk.PurgeBlink(ic)
    
    return (Lerr,Derr,TDOA,REAL,TDER)


def TDOF3(blk, tmr, remote, delay, rawts=False):

    #
    #     [1]             [2]              [3]
    #
    # (a)                 Ta2  --->--->--- Ta3
    #                                          \__delay[0]
    #                                          /
    # (b) Tb1 --->--->--- Tb2  --<>---<>-- Tb3
    #                                          \__delay[1]
    #                                          /
    # (c)                 Tc2  --->--->--- Tc3
    # 
    
    adr1 = remote[0].addr
    adr2 = remote[1].addr
    adr3 = remote[2].addr
    eui1 = remote[0].eui
    eui2 = remote[1].eui
    eui3 = remote[2].eui

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32
        
    Tm = tmr.sync()
    
    ia = blk.Blink(adr2,Tm)
    Tm = tmr.nap(delay[0])
    ib = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay[1])
    ic = blk.Blink(adr2,Tm)
    
    blk.WaitBlinks((ia,ib,ic),remote,delay[2])
    
    Ta2 = blk.getTS(ia, eui2, rawts)
    Ta3 = blk.getTS(ia, eui3, rawts)
    Tb2 = blk.getTS(ib, eui2, rawts)
    Tb3 = blk.getTS(ib, eui3, rawts)
    Tc2 = blk.getTS(ic, eui2, rawts)
    Tc3 = blk.getTS(ic, eui3, rawts)

    J12 = GetDistJiffies(eui1,eui2,SCL)
    J13 = GetDistJiffies(eui1,eui3,SCL)
    J23 = GetDistJiffies(eui2,eui3,SCL)

    Cdif = (Tc3 - Tc2) - J23
    dprint(' >>> Clock diff: {}'.format(Cdif))
    
    Dcb2 = Tc2 - Ta2
    Dcb3 = Tc3 - Ta3
    Drat = (Dcb3 - Dcb2) / (Dcb2 + Dcb3)
    dprint(' >>> Clock ratio: {:.3f}ppm'.format(Drat*1E6))
    
    TDOA = (Tb3 - Tb2) - Cdif + int((Tc3-Ta3)*Drat)
    REAL = J13 - J12
    TDER = TDOA - REAL
    dprint(' >>> TDOA:{} REAL:{} ERROR:{}'.format(TDOA,REAL,TDER))

    Derr = TDER / SCL
    Lerr = Derr * C_AIR * 1E-9
    dprint(' >>> Error: {:.3f}ns {:.3f}m'.format(Derr,Lerr))

    blk.PurgeBlink(ia)
    blk.PurgeBlink(ib)
    blk.PurgeBlink(ic)
    
    return (Lerr,Derr,TDOA,REAL,TDER)


def TDOF4(blk, tmr, remote, delay, rawts=False):

    #
    #     [1]             [2]              [3]
    #
    # (a)                 Ta2 ---->--->--- Ta3
    #                                          \__delay[0]
    #                                          /
    # (b) Tb1 --->--->--- Tb2 ---<>--<>--- Tb3
    #                                          \__delay[1]
    #                                          /
    # (c)                 Tc2 ---->--->--- Tc3
    #
    
    adr1 = remote[0].addr
    adr2 = remote[1].addr
    adr3 = remote[2].addr
    eui1 = remote[0].eui
    eui2 = remote[1].eui
    eui3 = remote[2].eui

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32
        
    Tm = tmr.sync()
    
    ia = blk.Blink(adr2,Tm)
    Tm = tmr.nap(delay[0])
    ib = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay[1])
    ic = blk.Blink(adr2,Tm)
    
    blk.WaitBlinks((ia,ib,ic),remote,delay[2])
    
    T1 = blk.getTS(ia, eui2, rawts)
    T2 = blk.getTS(ia, eui3, rawts)
    T3 = blk.getTS(ib, eui3, rawts)
    T4 = blk.getTS(ib, eui2, rawts)
    T5 = blk.getTS(ic, eui2, rawts)
    T6 = blk.getTS(ic, eui3, rawts)

    J12 = GetDistJiffies(eui1,eui2,SCL)
    J13 = GetDistJiffies(eui1,eui3,SCL)
    J23 = GetDistJiffies(eui2,eui3,SCL)
    dprint(' >>> J12:{} J13:{} J23:{}'.format(J12,J13,J23))
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    TTOT = 2 * (T41*T63 - T32*T54) // (T51+T62)
    TDOA = TTOT - J23
    REAL = J12 - J13
    TDER = TDOA - REAL
    dprint(' >>> TDOA:{} REAL:{} ERROR:{}'.format(TDOA,REAL,TDER))

    Derr = TDER / SCL
    Lerr = Derr * C_AIR * 1E-9
    dprint(' >>> Error: {:.3f}ns {:.3f}m'.format(Derr,Lerr))

    blk.PurgeBlink(ia)
    blk.PurgeBlink(ib)
    blk.PurgeBlink(ic)
    
    return (Lerr,Derr,TDOA,REAL,TDER)


def TDOF5(blk, tmr, remote, delay, rawts=False):

    #
    #     [1]             [2]              [3]
    #
    # (a) Ta1 --->--->--- Ta2 ---<>--<>--- Ta3
    #                                          \__delay[0]
    #                                          /
    # (b)                 Tb2 ---->--->--- Tb3
    #                                          \__delay[1]
    #                                          /
    # (c) Tc1 --->--->--- Tc2 ---<>--<>--- Tc3
    #
    
    adr1 = remote[0].addr
    adr2 = remote[1].addr
    adr3 = remote[2].addr
    eui1 = remote[0].eui
    eui2 = remote[1].eui
    eui3 = remote[2].eui

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32
        
    Tm = tmr.sync()
    
    ia = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay[0])
    ib = blk.Blink(adr2,Tm)
    Tm = tmr.nap(delay[1])
    ic = blk.Blink(adr1,Tm)
    
    blk.WaitBlinks((ia,ib,ic),remote,delay[2])
    
    T1 = blk.getTS(ia, eui3, rawts)
    T2 = blk.getTS(ia, eui2, rawts)
    T3 = blk.getTS(ib, eui2, rawts)
    T4 = blk.getTS(ib, eui3, rawts)
    T5 = blk.getTS(ic, eui3, rawts)
    T6 = blk.getTS(ic, eui2, rawts)

    J12 = GetDistJiffies(eui1,eui2,SCL)
    J13 = GetDistJiffies(eui1,eui3,SCL)
    J23 = GetDistJiffies(eui2,eui3,SCL)
    dprint(' >>> J12:{} J13:{} J23:{}'.format(J12,J13,J23))
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    TTOT = 2 * (T41*T63 - T32*T54) // (T51+T62)
    TDOA = TTOT - J23
    REAL = J12 - J13
    TDER = TDOA - REAL
    dprint(' >>> TDOA:{} REAL:{} ERROR:{}'.format(TDOA,REAL,TDER))

    Derr = TDER / SCL
    Lerr = Derr * C_AIR * 1E-9
    dprint(' >>> Error: {:.3f}ns {:.3f}m'.format(Derr,Lerr))

    blk.PurgeBlink(ia)
    blk.PurgeBlink(ib)
    blk.PurgeBlink(ic)
    
    return (Lerr,Derr,TDOA,REAL,TDER)


def main():
    
    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="OWR delay tool")

    DW1000.AddParserArguments(parser)
    
    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count, help='Number of blinks')
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay, help='Delay between blinks')
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait, help='Time to wait timestamp reception')
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT, help='UDP port')
    parser.add_argument('-A', '--algo', type=str, default=None, help='TWR algorithm')
    parser.add_argument('-H', '--hist', action='store_true', default=False, help='Print histogram')
    parser.add_argument('-P', '--plot', action='store_true', default=False, help='Plot histogram')
    parser.add_argument('-R', '--raw', action='store_true', default=False, help='Use raw timestamps')
    parser.add_argument('--range', type=float, default=CFG.range)
    parser.add_argument('--binsize', type=float, default=CFG.binsize)
    parser.add_argument('--delay1', type=float, default=None)
    parser.add_argument('--delay2', type=float, default=None)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    DEBUG = args.debug

    if args.algo is None:
        algo = TDOF5
    elif args.algo == 'TDOF1' or args.algo == '1':
        algo = TDOF1
    elif args.algo == 'TDOF2' or args.algo == '2':
        algo = TDOF2
    elif args.algo == 'TDOF3' or args.algo == '3':
        algo = TDOF3
    elif args.algo == 'TDOF4' or args.algo == '4':
        algo = TDOF4
    elif args.algo == 'TDOF5' or args.algo == '5':
        algo = TDOF5
    else:
        raise ValueError
    
    delay1 = args.delay
    delay2 = args.delay
    if args.delay1 is not None:
        delay1 = args.delay1
    if args.delay2 is not None:
        delay2 = args.delay2
    
    rpc = tail.RPC(('', args.port))

    remotes = [ ]
    for host in args.remote:
        try:
            anchor = DW1000(host,args.port,rpc)
            remotes.append(anchor)
        except:
            eprint('Remote {} exist does not'.format(host))

    DW1000.HandleArguments(args,remotes)
    
    if VERBOSE > 1:
        DW1000.PrintAllRemoteAttrs(remotes)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc, 0)

    delays = []
    errors = []

    eprints('Blinker starting..')

    try:
        for i in range(args.count):
            if i%10 == 0:
                eprints('.')

            try:
                (Lerr,Derr,TDOA,REAL,TDIF) = algo(blk, tmr, remotes, (delay1,delay2,args.wait), rawts=args.raw)

                if Lerr < -25.0 or Lerr > 25.0:
                    raise ValueError
                
                errors.append(Lerr)
                delays.append(Derr)

            except (TimeoutError):
                eprints('T')
            except (KeyError):
                eprints('?')
            except (ValueError):
                eprints('*')
            except (ZeroDivisionError):
                eprints('0')
                
    except KeyboardInterrupt:
        eprint('\nStopping...')
        args.plot = False
        args.hist = False

    blk.stop()
    rpc.stop()

    Tcnt = len(errors)
        
    if Tcnt > 0:

        Lavg = np.mean(errors)
        Lmed = np.median(errors)
        Lstd = np.std(errors)
        Davg = np.mean(delays)
        Dmed = np.median(delays)
        Dstd = np.std(delays)
        
        print()
        print('FINAL STATISTICS:')
        print('  Samples: {}'.format(Tcnt))
        print('  Rx Loss: {:.1f}%'.format(100-100*Tcnt/args.count))
        print('  Err Avg: {:.3f}m'.format(Lavg))
        print('  Err Dev: {:.3f}m'.format(Lstd))

        if args.hist or args.plot:
            
            Hbin = args.binsize
            if args.range > 0:
                Hrng = args.range
            else:
                Hrng = -2.0 * args.range * Dstd

            Hmin = Davg - Hrng/2
            Hmax = Davg + Hrng/2
            Hcnt = int(Hrng/Hbin) + 1
            bins = [ (N/Hcnt)*Hrng + Hmin for N in range(Hcnt+1) ]
        
            (hist,edges) = np.histogram(delays,bins=bins)

            if args.hist:
                print()
                print('HISTOGRAM:')
                for i in range(len(hist)):
                    print('   {:.3f}: {:d}'.format(edges[i],hist[i]))

            if args.plot:
                fig,ax = plot.subplots(figsize=(15,10),dpi=80)
                ax.set_title('Error distribution {} {} {}'.format(remotes[0].host,remotes[1].host,remotes[2].host))
                ax.set_xlabel('Error [ns]')
                ax.set_ylabel('Samples')
                ax.text(0.80, 0.95, r'$\mu$={:.3f}m'.format(Lavg), transform=ax.transAxes, size='x-large')
                ax.text(0.80, 0.90, r'$\sigma$={:.3f}m'.format(Lstd), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.95, r'$\mu$={:.3f}ns'.format(Davg), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.90, r'$\sigma$={:.3f}ns'.format(Dstd), transform=ax.transAxes, size='x-large')

                ax.grid(True)
                ax.hist(delays,bins)
                fig.tight_layout()
                plot.show()
        
    else:
        print()
        print('NO SUITABLE SAMPLES')

    

if __name__ == "__main__":
    main()

