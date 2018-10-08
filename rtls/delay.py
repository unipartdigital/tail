#!/usr/bin/python3
#
# Anchor distance tool for Tail algorithm development
#

import sys
import time
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
from tail import fpeak, eprint, eprints

from config import *


class Config():

    blink_count  = 100
    blink_delay  = 0.010
    blink_wait   = 0.250

    algo         = 'DECA'

    ewma         = 32
    range        = 1.000
    binsize      = 2 / DW1000_CLOCK_GHZ

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
    
    F2 = blk.getXtalPPM(i1, eui2)
    F6 = blk.getXtalPPM(i3, eui2)

    Pwr = blk.getRxPower(i1, eui2)
    Fpp = blk.getFpPower(i1, eui2)

    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    
    if rawts:
        Dof = Tof / DW1000_CLOCK_GHZ
        Rtt = T41 / DW1000_CLOCK_GHZ
    else:
        Dof = Tof / (1<<32)
        Rtt = T41 / (1<<32)
        
    Lof = Dof * C_AIR * 1E-9
        
    Est = (F2 + F6) / 2
    Err = (T62 - T51) / T62
    
    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Lof,Dof,Rtt,Err,Est,Pwr,Fpp)

            
def DECA_FAST_TWR(blk, tmr, remote, delay, rawts=False):
    
    adr1 = remote[0].addr
    adr2 = remote[1].addr
    eui1 = remote[0].eui
    eui2 = remote[1].eui

    Tm = tmr.sync()

    i1 = blk.GetBlinkId(Tm)
    i2 = blk.GetBlinkId(Tm)
    i3 = blk.GetBlinkId(Tm)

    blk.TriggerBlink(adr2,i1,i2)
    blk.TriggerBlink(adr1,i2,i3)
    
    tmr.nap(delay[0])
    
    blk.BlinkID(adr1,i1)
    
    blk.WaitBlinks((i1,i2,i3),remote,delay[2])
    
    T1 = blk.getTS(i1, eui1, rawts)
    T2 = blk.getTS(i1, eui2, rawts)
    T3 = blk.getTS(i2, eui2, rawts)
    T4 = blk.getTS(i2, eui1, rawts)
    T5 = blk.getTS(i3, eui1, rawts)
    T6 = blk.getTS(i3, eui2, rawts)
    
    F2 = blk.getXtalPPM(i1, eui2)
    F6 = blk.getXtalPPM(i3, eui2)

    Pwr = blk.getRxPower(i1, eui2)
    Fpp = blk.getFpPower(i1, eui2)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    
    if rawts:
        Dof = Tof / DW1000_CLOCK_GHZ
        Rtt = T41 / DW1000_CLOCK_GHZ
    else:
        Dof = Tof / (1<<32)
        Rtt = T41 / (1<<32)
        
    Lof = Dof * C_AIR * 1E-9
        
    Est = (F2 + F6) / 2
    Err = (T62 - T51) / T62
    
    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Lof,Dof,Rtt,Err,Est,Pwr,Fpp)

            
def main():
    
    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="TWR delay tool")

    DW1000.AddParserArguments(parser)
    
    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count, help='Number of blinks')
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay, help='Delay between blinks')
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait, help='Time to wait timestamp reception')
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT, help='UDP port')
    parser.add_argument('-A', '--algo', type=str, default=CFG.algo, help='TWR algorithm')
    parser.add_argument('-H', '--hist', action='store_true', default=False, help='Print histogram')
    parser.add_argument('-P', '--plot', action='store_true', default=False, help='Plot histogram')
    parser.add_argument('-R', '--raw', action='store_true', default=False, help='Use raw timestamps')
    parser.add_argument('--ewma', type=int, default=CFG.ewma)
    parser.add_argument('--range', type=float, default=CFG.range)
    parser.add_argument('--binsize', type=float, default=CFG.binsize)
    parser.add_argument('--delay1', type=float, default=None)
    parser.add_argument('--delay2', type=float, default=None)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    DEBUG = args.debug

    if args.algo == 'FAST':
        algo = DECA_FAST_TWR
    else:
        algo = DECA_TWR
        
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
    
    if VERBOSE > 0:
        DW1000.PrintAllRemoteAttrs(remotes)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc, args.debug)

    Tcnt = 0
    Rsum = 0.0
    Lfil = 0.0
    Lvar = 0.0

    delays = []
    powers = []
    fpathp = []
    rtrips = []

    eprint('Blinker starting')

    try:
        for i in range(args.count):
            try:
                (Lof,Dof,Rtt,Ppm,Ppe,Pwr,Fpp) = algo(blk, tmr, remotes, (delay1,delay2,args.wait), rawts=args.raw)
                if Lof > 0 and Lof < 100:
                    delays.append(Dof)
                    powers.append(Pwr)
                    fpathp.append(Fpp)
                    rtrips.append(Rtt/1E6)
                    Tcnt += 1
                    if VERBOSE > 0:
                        Plog = DW1000.RxPower2dBm(Pwr,64)
                        Ldif = Lof - Lfil
                        Lvar += (Ldif*Ldif - Lvar) / args.ewma
                        if Tcnt < args.ewma:
                            Lfil += Ldif / Tcnt
                        else:
                            Lfil += Ldif / args.ewma
                        print('{:.3f}m {:.3f}m -- Dist:{:.3f}m ToF:{:.3f}ns Xerr:{:+.3f}ppm Xest:{:+.3f}ppm Rx:{:.1f}dBm Rtt:{:.3f}ms'.format(Lfil,math.sqrt(Lvar),Lof,Dof,Ppm*1E6,Ppe*1E6,Plog,Rtt*1E-6))
                else:
                    if VERBOSE > 0:
                        eprint('*')
                    else:
                        eprints('*')
            except (ValueError,KeyError,TimeoutError):
                if VERBOSE > 0:
                    eprint('?')
                else:
                    eprints('?')
            if VERBOSE == 0 and i%10 == 0:
                eprints('.')
            
    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    if Tcnt > 0:
        Davg = np.mean(delays)
        Dstd = np.std(delays)
        Dmed = np.median(delays)
        Pavg = np.mean(powers)
        Pstd = np.std(powers)
        Favg = np.mean(fpathp)
        Fstd = np.std(fpathp)
        Lavg = Davg * C_AIR * 1E-9
        Lstd = Dstd * C_AIR * 1E-9
        Lmed = Dmed * C_AIR * 1E-9
        Plog = DW1000.RxPower2dBm(Pavg,64)
        Pstl = DW1000.RxPower2dBm(Pavg+Pstd,64) - Plog
        Flog = DW1000.RxPower2dBm(Favg,64)
        Fstl = DW1000.RxPower2dBm(Favg+Fstd,64) - Flog
        Ravg = np.mean(rtrips)
        Rstd = np.std(rtrips)

        (Navg,Nstd) = fpeak(delays)
        
        Mavg = Navg * C_AIR * 1E-9
        Mstd = Nstd * C_AIR * 1E-9
        
        print()
        print('FINAL STATISTICS:')
        print('  Samples:  {} [{:.1f}%]'.format(Tcnt,100*Tcnt/args.count))
        print('  Peak.Avg: {:.3f}m {:.3f}ns'.format(Mavg,Navg))
        print('  Peak.Std: {:.3f}m {:.3f}ns'.format(Mstd,Nstd))
        print('  Average:  {:.3f}m {:.3f}ns'.format(Lavg,Davg))
        print('  Std.Dev:  {:.3f}m {:.3f}ns'.format(Lstd,Dstd))
        print('  Median:   {:.3f}m {:.3f}ns'.format(Lmed,Dmed))
        print('  RTT.Avg:  {:.3f}ms {:.3f}ms'.format(Ravg,Rstd))
        print('  PWR.Avg:  {:.1f}dBm {:.2f}dBm'.format(Plog,Pstl))
        print('  FPP.Avg:  {:.1f}dBm {:.2f}dBm'.format(Flog,Fstl))

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
                ax.set_title('Delay distribution {} - {} @ {}'.format(remotes[0].host,remotes[1].host,
                                                                      time.strftime('%d/%m/%Y %H:%M:%S')))
                ax.set_xlabel('Delay [ns]')
                ax.set_ylabel('Samples')
                ax.text(0.80, 0.95, r'P={:.3f}m'.format(Mavg), transform=ax.transAxes, size='x-large')
                ax.text(0.80, 0.90, r'p={:.3f}m'.format(Mstd), transform=ax.transAxes, size='x-large')
                ax.text(0.80, 0.85, r'$\mu$={:.3f}m'.format(Lavg), transform=ax.transAxes, size='x-large')
                ax.text(0.80, 0.80, r'$\sigma$={:.3f}m'.format(Lstd), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.95, r'P={:.3f}ns'.format(Navg), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.90, r'p={:.3f}ns'.format(Nstd), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.85, r'$\mu$={:.3f}ns'.format(Davg), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.80, r'$\sigma$={:.3f}ns'.format(Dstd), transform=ax.transAxes, size='x-large')
                ax.grid(True)
                ax.hist(delays,bins)
                fig.tight_layout()
                plot.show()
        
    else:
        print()
        print('NO SUITABLE SAMPLES')


if __name__ == "__main__":
    main()

