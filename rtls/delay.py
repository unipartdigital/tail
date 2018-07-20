#!/usr/bin/python3
#
# Anchor distance tool for Tail algorithm development
#

import argparse
import socket
import pprint
import threading
import queue
import json
import math
import tail
import sys

import numpy as np
import numpy.linalg as lin

from numpy import dot

from tail import eprint


class Config():

    Cns = 0.299705
    #Cns = 0.299792458
    
    blink_delay  = 0.010
    blink_speed  = 100
    blink_count  = 100
    
    rpc_port   = 61666

    dw1000_rate  = 6800
    dw1000_txpsr = 256
    dw1000_xtalt = 0x0f
    dw1000_antd  = 0x402c

    dw1000_attrs = (
        'snr_threshold',
        'fpr_threshold',
        'noise_threshold',
        'channel',
        'pcode',
        'txpsr',
        'prf',
        'rate',
        'antd',
        'xtalt',
        'smart_power',
    )


cfg = Config()


def getEUIs(blks,index,direc):
    euis = []
    if index is not None:
        if index in blks:
            for anc in blks[index]:
                if 'dir' in blks[index][anc]:
                    if blks[index][anc]['dir'] == direc:
                        euis.append(anc)
    return euis
                    

def getTS(blks,index,eui,direc):
    if blks[index][eui]['dir'] == direc:
        return blks[index][eui]['tss']
    raise ValueError
    

def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")

    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    parser.add_argument('-s', '--speed', type=float, default=cfg.blink_speed)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    
    parser.add_argument('--rate', type=int, default=cfg.dw1000_rate)
    parser.add_argument('--txpsr', type=int, default=cfg.dw1000_txpsr)
    parser.add_argument('--xtalt', type=str, default=None)
    parser.add_argument('--antd', type=str, default=None)
    
    parser.add_argument('remotes', type=str, nargs='+', help="Remote addresses")
    
    args = parser.parse_args()

    blink_delay = args.delay
    blink_count = args.count

    blink_wait = max((1.0 / args.speed) - 3*blink_delay,0)

    remotes = [ ]
    
    for host in args.remotes:
        addr = socket.getaddrinfo(host, args.port, socket.AF_INET6)[0][4]
        remotes.append( { 'host': host, 'addr': addr, 'EUI': None } )
    
    rem_addr = [ rem['addr'] for rem in remotes ]
    
    rpc = tail.RPC(('', args.port))

    for remote in remotes:
        remote['EUI'] = rpc.getEUI(remote['addr'])
        
    for addr in rem_addr:
        rpc.setAttr(addr, 'rate', args.rate)
        rpc.setAttr(addr, 'txpsr', args.txpsr)
        if args.xtalt is not None:
            rpc.setAttr(addr, 'xtalt', int(args.xtalt,0))
        if args.antd is not None:
            rpc.setAttr(addr, 'antd', int(args.antd,0))
        
    for remote in remotes:
        addr = remote['addr']
        eprint('DW1000 parameters @{} <{}>'.format(remote['host'],remote['EUI']))
        for attr in cfg.dw1000_attrs:
            val = rpc.getAttr(addr, attr)
            eprint('  {}={}'.format(attr, val))

    blk = tail.Blinker(rpc,remotes)
    tmr = tail.Timer()

    Tcnt = 0
    Tsum = 0
    Dsum = 0.0
    Dsqr = 0.0

    ADR1 = remotes[0]['addr']
    ADR2 = remotes[1]['addr']

    EUI1 = remotes[0]['EUI']
    EUI2 = remotes[1]['EUI']

    eprint('Blinker starting')

    try:
        for i in range(blink_count):
        
            #if i % 100 == 0:
            #    eprint(end='.', flush=True)
            
            Tm = tmr.nap(blink_wait)
            I1 = blk.Blink(ADR1, Tm)

            Tm = tmr.nap(blink_delay)
            I2 = blk.Blink(ADR2, Tm)

            Tm = tmr.nap(blink_delay)
            I3 = blk.Blink(ADR1, Tm)

            Tm = tmr.nap(blink_delay)

            try:
                T1 = getTS(blk.blinks, I1, EUI1, 'TX')
                T2 = getTS(blk.blinks, I1, EUI2, 'RX')
                T3 = getTS(blk.blinks, I2, EUI2, 'TX')
                T4 = getTS(blk.blinks, I2, EUI1, 'RX')
                T5 = getTS(blk.blinks, I3, EUI1, 'TX')
                T6 = getTS(blk.blinks, I3, EUI2, 'RX')

                T41 = T4 - T1
                T32 = T3 - T2
                T54 = T5 - T4
                T63 = T6 - T3

                Tof = (T41*T63 - T32*T54) / (T41+T32+T54+T63)
                Dof = Tof / (1<<32)
                Lof = Dof * cfg.Cns

                if Lof > 0 and Lof < 50:
                    Tcnt += 1
                    Tsum += Tof
                    Dsum += Dof
                    Dsqr += Dof*Dof
                    print('{:.3f}m {:.3f}ns'.format(Lof,Dof))
                
            except (ValueError,KeyError):
                eprint('?')
            
        Tavg = Tsum/Tcnt
        Davg = Dsum/Tcnt
        Dvar = Dsqr/Tcnt - Davg*Davg
        Dstd = math.sqrt(Dvar)
        Lavg = Davg * cfg.Cns
        Lstd = Dstd * cfg.Cns

        print('FINAL STATISTICS:')
        print('  Samples:  {}'.format(Tcnt))
        print('  Average:  {:.3f}m {:.3f}ns'.format(Lavg,Davg))
        print('  Std.Dev:  {:.3f}m {:.3f}ns'.format(Lstd,Dstd))

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    

if __name__ == "__main__":
    main()

