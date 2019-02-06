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

    window         = 100000

CFG = Config()


def XTAL_PPM(blk, tmr, tx, rxs, devs, CH=7, PRF=64, rawts=False):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32

    veprint(1,'\n** BLINK {} <{}>'.format(tx.host,tx.eui))

    tm = tmr.sync()
    i1 = blk.Blink(tx,tm)
    tm = tmr.nap(CFG.blink_delay)
    i2 = blk.Blink(tx,tm)

    blk.WaitBlinks((i1,i2),devs,CFG.blink_wait)
        
    Fcnt = 0
    Fsum = 0.0
    Esum = 0.0
    Psum = 0.0

    DATA = {}
    
    for rx in rxs:
        try:
            T1 = blk.getTS(i1, tx.eui, rawts)
            T2 = blk.getTS(i1, rx.eui, rawts)
            T3 = blk.getTS(i2, tx.eui, rawts)
            T4 = blk.getTS(i2, rx.eui, rawts)

            S2 = blk.getTSW(i1, rx.eui)
            
            F2 = blk.getXtalPPM(i1, rx.eui)
            F4 = blk.getXtalPPM(i2, rx.eui)
            
            P2 = blk.getRxPower(i1, rx.eui)
            P4 = blk.getRxPower(i2, rx.eui)

            P24 = (P2+P4)/2
            F24 = (F2 + F4) / 2
            
            T31 = T3 - T1
            T42 = T4 - T2
            
            Err = (T42 - T31) / T42
            Pwr = DW1000.RxPower2dBm(P24,PRF)
            
            Fcnt += 1
            Esum += Err
            Fsum += F24
            Psum += P24

            key = rx.host
            
            DATA[key] = {}
            DATA[key]['PPM'] = Err
            DATA[key]['PWR'] = Pwr
            DATA[key]['HWT'] = T2
            DATA[key]['SWT'] = S2

            veprint(1, '    {:<12s}  {:7.3f}ppm {:7.3f}ppm {:6.1f}dBm'.format(rx.host,Err*1E6,F24*1E6,Pwr))
                
        except (ValueError,KeyError):
            veprint(1,'    {:<12s}'.format(rx.host,rx.eui))

    Eavg = Esum/Fcnt
    Favg = Fsum/Fcnt
    Pavg = Psum/Fcnt
    
    Pwr = DW1000.RxPower2dBm(Pavg,PRF)
                
    veprint(1,'    =============================================')
    veprint(1,'    AVERAGE       {:7.3f}ppm {:7.3f}ppm {:6.1f}dBm'.format(Eavg*1E6,Favg*1E6,Pwr))

    return (Eavg,Favg,Pavg,Fcnt,DATA)


def main():
    
    parser = argparse.ArgumentParser(description="XTAL NTP test")

    DW1000.AddParserArguments(parser)

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-i', '--interval', type=float, default=CFG.blink_interval)
    parser.add_argument('-W', '--window', type=float, default=CFG.window)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-f', '--file', type=str, default=None)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    tail.VERBOSE = args.verbose
    
    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait = args.wait
    CFG.blink_interval = args.interval
    CFG.window = args.window
    
    if args.file is not None:
        fd = open(args.file, 'a')
    else:
        fd = None
    
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
    
    Scnt = 0
    Bcnt = 0
    Fsum = 0.0
    Esum = 0.0
    Psum = 0.0
    
    DATA = {}
    
    eprint('Blinker starting')

    try:
        for i in range(CFG.blink_count):

            try:
                (Eavg,Favg,Pavg,Fcnt,Data) = XTAL_PPM(blk, tmr, xmitters[0], rceivers, remotes, CH=ch, PRF=prf)

                Bcnt += 1
                Scnt += Fcnt
                Esum += Eavg*Fcnt
                Fsum += Favg*Fcnt
                Psum += Pavg*Fcnt

                DATA[i] = Data

                W = int(CFG.window / CFG.blink_interval)
                a = i
                b = max(0,i-W)
                
                veprint(1, '\nSW/HW drift estimate [{}]:'.format(a-b))

                msg = '{}'.format(i)
                
                for rx in rceivers:
                    key = rx.host
                    ppm = DATA[a][key]['PPM']
                    msg += ',:{:.3f}'.format(ppm*1E6)
                    try:
                        H0 = DATA[b][key]['HWT']
                        H1 = DATA[a][key]['HWT']
                        H10 = H1 - H0
                        S0 = DATA[b][key]['SWT']
                        S1 = DATA[a][key]['SWT']
                        S10 = S1 - S0
                        Esw = (H10 - S10) / S10
                        veprint(1, '    {:<12s}  {:7.3f}ppm'.format(rx.host,Esw*1E6))
                        msg += ',{},{}'.format(H1,S1)
                    except:
                        veprint(1, '    {:<12s}  ???'.format(rx.host))
                        msg += ',,'

                if fd is not None:
                    fd.write(msg + '\n')
                        
                tm = tmr.nap(CFG.blink_interval)

            except (ValueError,KeyError,ZeroDivisionError,TimeoutError):
                pass
            
    except KeyboardInterrupt:
        eprint('\nStopping...')

    if fd is not None:
        fd.close()
        
    blk.stop()
    rpc.stop()

    if Scnt > 0:
        
        Favg = Fsum/Scnt
        Eavg = Esum/Scnt
        Pavg = Psum/Scnt
        
        Pwr = DW1000.RxPower2dBm(Pavg,prf)
                
        ##pprint(DATA)
    
        print()
        print('FINAL STATISTICS:')
        print('  Blinks:   {}'.format(Bcnt))
        print('  Samples:  {}'.format(Scnt))
        print('  XTAL:     {:.3f}ppm'.format(Eavg*1E6))
        print('  TTCK:     {:.3f}ppm'.format(Favg*1E6))
        print('  POWER:    {:.1f}dBm'.format(Pwr))
        

if __name__ == "__main__":
    main()

