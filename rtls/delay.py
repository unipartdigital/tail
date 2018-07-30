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

from tail import DW1000
from tail import eprint


class Config():

    Cns = 0.299705
    #Cns = 0.299792458

    ewma = 32
    
    blink_delay  = 0.010
    blink_speed  = 100
    blink_count  = 100
    
    rpc_port   = 61666


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
                    

def getTS(blks,index,eui,direc,raw=False):
    if blks[index][eui]['dir'] == direc:
        if raw:
            return blks[index][eui]['tsi']['rawts']
        else:
            return blks[index][eui]['tss']
    raise ValueError
    

def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")

    DW1000.AddParserOptions(parser)
    
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    parser.add_argument('-s', '--speed', type=float, default=cfg.blink_speed)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('-E', '--ewma', type=int, default=cfg.ewma)
    
    parser.add_argument('-R', '--raw', action='store_true', default=False)
    
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    ewma = args.ewma
    rawts = args.raw

    blink_delay = args.delay
    blink_count = args.count

    blink_wait = max((1.0 / args.speed) - 3*blink_delay,0)

    remotes = [ ]
    
    for host in args.remote:
        addr = socket.getaddrinfo(host, args.port, socket.AF_INET6)[0][4]
        remotes.append( { 'host': host, 'addr': addr, 'EUI': None } )
    
    rem_addr = [ rem['addr'] for rem in remotes ]
    
    rpc = tail.RPC(('', args.port))

    for remote in remotes:
        remote['EUI'] = rpc.getEUI(remote['addr'])

    DW1000.HandleArguments(args,rpc,rem_addr)

    eprint('DW1000 Attributes:')
    
    for remote in remotes:
        eprint('\n{} <{}>'.format(remote['host'],remote['EUI']))
        DW1000.PrintRemoteAttrs(rpc,remote['addr'])

    eprint()


    blk = tail.Blinker(rpc,remotes)
    tmr = tail.Timer()

    Tcnt = 0
    Tsum = 0
    Dsum = 0.0
    Dsqr = 0.0
    Lfil = 0.0

    ADR1 = remotes[0]['addr']
    ADR2 = remotes[1]['addr']

    EUI1 = remotes[0]['EUI']
    EUI2 = remotes[1]['EUI']

    eprint('Blinker starting')

    try:
        for i in range(blink_count):
        
            Tm = tmr.nap(blink_wait)
            i1 = blk.Blink(ADR1,Tm)

            Tm = tmr.nap(blink_delay)
            i2 = blk.Blink(ADR2,Tm)

            Tm = tmr.nap(blink_delay)
            i3 = blk.Blink(ADR1,Tm)

            Tm = tmr.nap(blink_delay)

            try:
                T1 = getTS(blk.blinks, i1, EUI1, 'TX', rawts)
                T2 = getTS(blk.blinks, i1, EUI2, 'RX', rawts)
                T3 = getTS(blk.blinks, i2, EUI2, 'TX', rawts)
                T4 = getTS(blk.blinks, i2, EUI1, 'RX', rawts)
                T5 = getTS(blk.blinks, i3, EUI1, 'TX', rawts)
                T6 = getTS(blk.blinks, i3, EUI2, 'RX', rawts)

                T41 = T4 - T1
                T32 = T3 - T2
                T54 = T5 - T4
                T63 = T6 - T3
                T51 = T5 - T1
                T62 = T6 - T2

                Frt = (T51 - T62) / T51
                Tof = (T41*T63 - T32*T54) / (T51+T62)
                if rawts:
                    Dof = Tof / 63.8976
                else:
                    Dof = Tof / (1<<32)
                Lof = Dof * cfg.Cns

                if Lof > 0 and Lof < 100:
                    Tcnt += 1
                    Tsum += Tof
                    Dsum += Dof
                    Dsqr += Dof*Dof
                    if Tcnt < ewma:
                        Lfil += (Lof - Lfil) / Tcnt
                    else:
                        Lfil += (Lof - Lfil) / ewma
                    
                    print('{:.3f}m -- {:.3f}m {:.3f}ns {:.3f}ppm'.format(Lfil,Lof,Dof,Frt*1E6))
                
            except (ValueError,KeyError):
                eprint('?')
            
    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    try:
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

    except:
        pass


if __name__ == "__main__":
    main()

