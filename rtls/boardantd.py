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
    blink_wait   = 0.050

    rawts        = 0

    algo         = 'DECA'

CFG = Config()

VERBOSE = 0

ANCHORS = (
    'bss1',
    'bss2',
    'bss3',
    'bss4',
    'bss5',
    'bss6',
    'bss7',
    'bss8',
)

IGNORE = [
    (4,5),
    (6,7),
]


def norm(x):
    return math.sqrt(x[0]*x[0] + x[1]*x[1] + x[2]*x[2])

def eucl(x,y):
    return math.sqrt((x[0]-y[0])*(x[0]-y[0]) + (x[1]-y[1])*(x[1]-y[1]) + (x[2]-y[2])*(x[2]-y[2]))


def DECA_TWR(anc1, anc2, delay1, delay2, blk, tmr):
    
    adr1 = anc1.addr
    adr2 = anc2.addr

    eui1 = anc1.eui
    eui2 = anc2.eui

    Tm = tmr.get()
    
    i1 = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay1)
    
    i2 = blk.Blink(adr2,Tm)
    Tm = tmr.nap(delay1)
    
    i3 = blk.Blink(adr1,Tm)
    Tm = tmr.nap(delay2)

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

    Tm = tmr.get()

    i1 = blk.GetBlinkId(Tm)
    i2 = blk.GetBlinkId(Tm)
    i3 = blk.GetBlinkId(Tm)

    blk.TriggerBlink(adr2,i1,i2)
    blk.TriggerBlink(adr1,i2,i3)
    
    tmr.nap(delay1)
    
    blk.BlinkID(adr1,i1)
    
    tmr.nap(delay2)
    
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
    
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-A', '--algo', type=str, default=CFG.algo)
    parser.add_argument('-R', '--raw', action='store_true', default=False)
    
    args = parser.parse_args()

    VERBOSE = args.verbose

    CFG.algo = args.algo
    CFG.rawts = args.raw
    
    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait = args.wait

    rpc = tail.RPC(('',args.port))

    remotes = { }
    for i in range(8):
        try:
            remotes[i] = DW1000(ANCHORS[i],args.port,rpc)
        except:
            eprint('In DNS anchor {} exist does not'.format(ANCHORS[i]))

    DW1000.HandleArguments(args,remotes.values())
    
    if VERBOSE > 0:
        DW1000.PrintAllRemoteAttrs(remotes.values())

    tmr = tail.Timer()
    blk = tail.Blinker(rpc, args.debug)

    try:
        dist = np.zeros((8,8))
        dvar = np.zeros((8,8))
        derr = np.zeros((8,8))
        for i1 in range(8):
            rem1 = remotes[i1]
            for i2 in range(8):
                rem2 = remotes[i2]
                if (i1,i2) in IGNORE:
                    dist[i1,i2] = 0.0
                elif i2 > i1:
                    Lstd = 1.0
                    while Lstd > 0.100:
                        print('Ranging {} to {}'.format(rem1.host,rem2.host))
                        Tcnt = 0
                        Lsum = 0.0
                        Lsqr = 0.0
                        for i in range(CFG.blink_count):
                            try:
                                if CFG.algo == 'DECA':
                                    (Lof,Dof,Rtt,Err,Est,Pwr) = DECA_TWR(rem1, rem2, CFG.blink_delay, CFG.blink_wait, blk, tmr)
                                elif CFG.algo == 'FAST':
                                    (Lof,Dof,Rtt,Err,Est,Pwr) = DECA_FAST_TWR(rem1, rem2, CFG.blink_delay, CFG.blink_wait, blk, tmr)
                                if Lof > 0 and Lof < 20:
                                    Tcnt += 1
                                    Lsum += Lof
                                    Lsqr += Lof*Lof
                            except (ValueError,KeyError):
                                eprint(end='?', flush=True)
                            if i%10 == 0:
                                eprint(end='.', flush=True)
                        if Tcnt > 0:
                            Lavg = Lsum/Tcnt
                            Lvar = Lsqr/Tcnt - Lavg*Lavg
                            Lstd = math.sqrt(Lvar)
                            dist[i1,i2] = Lavg
                            dvar[i1,i2] = Lvar
                            print('   = {:.3f}m {:.3f}m'.format(Lavg,Lstd))
                        else:
                            dist[i1,i2] = None
                            dvar[i1,i2] = None
                            print('FAIL')
                elif i1 > i2:
                    dist[i1,i2] = dist[i2,i1]
                    dvar[i1,i2] = dvar[i2,i1]
                else:
                    dist[i1,i2] = 0.0
                    dvar[i1,i2] = 0.0
                    
                derr[i1,i2] = dist[i1,i2] - eucl(QS_BOARD_ROOM_COORD[i1],QS_BOARD_ROOM_COORD[i2])
                
        #print(dist)

        L = 28 - len(IGNORE)

        A = np.zeros((L,8))
        G = np.zeros((L))
        C = np.zeros((L))
        k = 0
        for i1 in range(8):
            for i2 in range(i1+1,8):
                if (i1,i2) not in IGNORE:
                    print('adding {},{}'.format(i1,i2))
                    A[k,i1] = 1
                    A[k,i2] = 1
                    G[k] = dvar[i1,i2]
                    C[k] = derr[i1,i2]
                    k += 1

        GG = np.diag(1/G)
        AA = dot(dot(A.T,GG),A)
        AC = dot(dot(A.T,GG),C)
        AB = lin.solve(AA,AC)
        ANTD = (AB/C_AIR) * DW_CLOCK_GHZ * 1E9

        print(ANTD)

        for i in range(8):
            antd = remotes[i].GetAttr('antd')
            newd = int(antd,0) + int(ANTD[i])
            remotes[i].SetAttr('antd', newd)
            antd = remotes[i].GetAttr('antd')
            print('{} <{}> antd={}'.format(remotes[i].host, remotes[i].eui, antd))

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()



if __name__ == "__main__":
    main()
