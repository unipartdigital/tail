#!/usr/bin/python3
#
# Tx Power calibration for Tail algorithm development
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

from tail import *
from config import *


class Config():

    rx_power     = -75.0
    at_total     = None
    
    tx_power     = [0,8]
    tx_coarse    = None

    rawts        = True
    
    blink_count  = 100
    blink_delay  = 0.010
    blink_wait   = 0.100

CFG = Config()

VERBOSE = 0


PI = math.pi
CS = 299792458
CC = 4*PI/CS
FC = ( None, 3494.4, 3993.6, 4492.8, 3993.6, 6489.6, None, 6489.6 )

def DAI(m,fc,pt):
    return pt - 20*np.log10(m*CC*fc*1e6)


def TxPwrs2Hex(txpwr):
    a = txpwr[0]
    b = txpwr[1]
    c = int(a / 3)
    d = int(b * 2)
    if c<0 or c>6:
        raise ValueError
    if d<0 or d>31:
        raise ValueError
    e = (6 - c) << 5
    f = (e|d)
    return '0x{:02x}'.format(f)


def PWRTWR(blk, tmr, remote, delay, txpwr=None, rawts=False):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32

    rem1 = remote[0]
    rem2 = remote[1]
    
    adr1 = rem1.addr
    adr2 = rem2.addr
    eui1 = rem1.eui
    eui2 = rem2.eui

    if txpwr is not None:
        rem1.SetAttr('tx_power', TxPwrs2Hex(txpwr[0]))
        rem2.SetAttr('tx_power', TxPwrs2Hex(txpwr[1]))
    
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
    
    P1 = blk.getRxPower(i2, eui1)
    P2 = blk.getRxPower(i1, eui2)
    
    F1 = blk.getFpPower(i2, eui1)
    F2 = blk.getFpPower(i1, eui2)

    C1 = blk.getTemp(i1,eui1)
    C2 = blk.getTemp(i2,eui2)
    
    V1 = blk.getVolt(i1,eui1)
    V2 = blk.getVolt(i2,eui2)
    
    S1 = blk.getSNR(i2,eui1)
    S2 = blk.getSNR(i1,eui2)
    
    N1 = blk.getNoise(i2,eui1)
    N2 = blk.getNoise(i1,eui2)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    PPM = 1E6 * (T62 - T51) / T62

    Tof = (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / SCL
    Lof = Dof * CS * 1E-9
    
    if Lof < 0 or Lof > 100:
        raise ValueError
    
    Time = blk.getTime(i1)
    
    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Time,remote[0].host,remote[1].host, Dof,Lof, txpwr, PPM, S1,P1,F1,N1,C1,V1, S2,P2,F2,N2,C2,V2)


def main():
    
    global VERBOSE
    
    parser = argparse.ArgumentParser(description="RTLS server")

    DW1000.AddParserArguments(parser)

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-R', '--raw', action='store_true', default=False)
    parser.add_argument('-P', '--power', type=float, default=CFG.rx_power)
    parser.add_argument('-A', '--atten', type=float, default=CFG.at_total)
    parser.add_argument('-C', '--coarse', type=int, default=CFG.tx_coarse)
    
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    VERBOSE = args.verbose

    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait = args.wait

    rpc = tail.RPC(('', args.port))
    
    remotes  = [ ]
    
    for host in args.remote:
        try:
            anchor = DW1000(host,args.port,rpc)
            remotes.append(anchor)
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

    ch  = int(remotes[0].GetAttr('channel'))
    prf = int(remotes[0].GetAttr('prf'))
    
    txpwr = [ list(CFG.tx_power), list(CFG.tx_power) ]

    if args.coarse is not None:
        txpwr[0][0] = args.coarse
        txpwr[1][0] = args.coarse
        
    try:
        while True:

            dofs = []
            ppms = []
            
            pwrs = ([],[])
            fprs = ([],[])
            tmps = ([],[])
            
            Tcnt = 0

            if VERBOSE>2:
                print('\rTx: {0[0]:d}{0[1]:+.1f}dBm {1[0]:d}{1[1]:+.1f}dBm'.format(txpwr[0],txpwr[1]))
    
            for i in range(CFG.blink_count):
                try:
                    
                    DATA = PWRTWR(blk, tmr, remotes, (args.delay,args.delay,args.wait), txpwr, rawts=args.raw)
                    (Time, _,_, Dof,Lof,_, PPM, S1,P1,F1,N1,C1,V1, S2,P2,F2,N2,C2,V2) = DATA

                    if Lof < 0 or Lof > 100:
                        raise ValueError

                    Tcnt += 1
                
                    dofs.append(Dof)
                    ppms.append(PPM)
                    
                    pwrs[0].append(P1)
                    pwrs[1].append(P2)
                    fprs[0].append(F1)
                    fprs[1].append(F2)
                    tmps[0].append(C1)
                    tmps[1].append(C2)

                    if VERBOSE>2:
                        prints('\rRx: {:.1f}dBm {:.1f}dBm '.format(DW1000.RxPower2dBm(P1,prf),
                                                                   DW1000.RxPower2dBm(P2,prf)))
                    elif VERBOSE>1:
                        if Tcnt%10==0:
                            prints('.')

                except (TimeoutError):
                    eprints('T')
                except (KeyError):
                    eprints('?')
                except (ValueError):
                    eprints('*')
                except (ZeroDivisionError):
                    eprints('0')

            try:
                
                if Tcnt < 10:
                    raise ValueError
            
                Davg = np.mean(dofs)
                Dstd = np.std(dofs)
                Dmed = np.median(dofs)
                
                Lavg = Davg * CS * 1E-9
                Lstd = Dstd * CS * 1E-9
                Lmed = Dmed * CS * 1E-9
                
                (Navg,Nstd) = fpeak(dofs)
        
                Mavg = Navg * CS * 1E-9
                Mstd = Nstd * CS * 1E-9

                PPMavg = np.mean(ppms)
                PPMstd = np.std(ppms)
                
                P0avg = np.mean(pwrs[0])
                P0std = np.std(pwrs[0])
                P1avg = np.mean(pwrs[1])
                P1std = np.std(pwrs[1])
                
                P0log = DW1000.RxPower2dBm(P0avg,prf)
                P0stl = DW1000.RxPower2dBm(P0avg+P0std,prf) - P0log
                P1log = DW1000.RxPower2dBm(P1avg,prf)
                P1stl = DW1000.RxPower2dBm(P1avg+P1std,prf) - P1log

                T0avg = np.mean(tmps[0])
                T0std = np.std(tmps[0])
                T1avg = np.mean(tmps[1])
                T1std = np.std(tmps[1])

                if args.atten is not None:
                    target_power = DAI(Lavg,FC[ch],args.atten)
                else:
                    target_power = args.power

                print('\n')
                print('STATISTICS: [CH{},PRF{}]'.format(ch,prf))
                print('    Samples:   {} [{:.1f}%]'.format(Tcnt,(100*Tcnt/args.count)-100))
                print('    Peak.Avg:  {:.3f}m ~{:.3f}ns'.format(Mavg,Navg))
                print('    Peak.Std:  {:.3f}m ~{:.3f}ns'.format(Mstd,Nstd))
                print('    Average:   {:.3f}m ~{:.3f}ns'.format(Lavg,Davg))
                print('    Median:    {:.3f}m ~{:.3f}ns'.format(Lmed,Dmed))
                print('    StdDev:    {:.3f}m ~{:.3f}ns'.format(Lstd,Dstd))
                print('    Xtal:      {:+.2f}ppm [{:.2f}ppm]'.format(PPMavg,PPMstd))
                print('    Temp#1:    {:.1f}°C [{:.2f}°C]'.format(T0avg,T0std))
                print('    Temp#2:    {:.1f}°C [{:.2f}°C]'.format(T1avg,T1std))
                print('    TxPWR#1:   {0:+.1f}dBm [{1[0]:d}{1[1]:+.1f}]'.format(txpwr[0][0]+txpwr[0][1], txpwr[0]))
                print('    TxPWR#2:   {0:+.1f}dBm [{1[0]:d}{1[1]:+.1f}]'.format(txpwr[1][0]+txpwr[1][1], txpwr[1]))
                print('    RxPWR#1:   {:.1f}dBm [{:.2f}dBm]'.format(P0log,P0stl))
                print('    RxPWR#2:   {:.1f}dBm [{:.2f}dBm]'.format(P1log,P1stl))
                print()

                
                ##
                ## Adjust Tx Power
                ##
                
                if txpwr[0][1] > 0 and P1log > target_power + 0.25:
                    txpwr[0][1] -= 0.5
                if txpwr[0][1] < 15.5 and P1log < target_power - 0.25:
                    txpwr[0][1] += 0.5
                
                if txpwr[1][1] > 0 and P0log > target_power + 0.25:
                    txpwr[1][1] -= 0.5
                if txpwr[1][1] < 15.5 and P0log < target_power - 0.25:
                    txpwr[1][1] += 0.5

                if txpwr[0][1] < 0:
                    txpwr[0][1] = 0.0
                if txpwr[0][1] > 15.5:
                    txpwr[0][1] = 15.5
                
                if txpwr[1][1] < 0:
                    txpwr[1][1] = 0.0
                if txpwr[1][1] > 15.5:
                    txpwr[1][1] = 15.5

            except Exception as err:
                eprint('This sucks: {}'.format(err))
                
    except (KeyboardInterrupt):
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    

if __name__ == "__main__":
    main()

