#!/usr/bin/python3
#
# Location tool for algorithm development
#

import sys
import math
import queue
import socket
import json
import pprint
import argparse
import threading
import traceback
import tail
import tdoa

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plt

from numpy import dot

from tail import DW1000
from tail import eprint, eprints

from config import *


class Config():

    blink_delay  = 0.020
    blink_wait   = 0.250

    sigma = 1E-7
    round = 0.050
    ewma = 8

CFG = Config()

VERBOSE = 0
DEBUG = 0

TAGS = {
    'Tcnt'   : 1,
    'Tavg'   : np.array((0,0,0)),
    'Vavg'   : 0.0,
}

ROOM_SIZE = ((-0.25,9.0),(-0.25,6.5))

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


## Helper functions

def dprint(*args, **kwargs):
    if DEBUG > 0:
        print(*args, file=sys.stderr, flush=True, **kwargs)


def pround(x,p):
    return p*np.round(x/p)
        
def GetDist(eui1,eui2):
    i = DW1000_DEVICE_CALIB[eui1]['bss']
    j = DW1000_DEVICE_CALIB[eui2]['bss']
    return BSS_DIST[i][j]

def GetDistJiffies(eui1,eui2,SCL):
    return int(round(GetDist(eui1,eui2)/C_AIR * SCL * 1E9))


## Visualisation

class room():

    def __init__(self):

        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1,1,1)

        self.fig.set_size_inches(16,10)

        self.ax1.set_title('Tag Location')
        self.ax1.set_xlim(ROOM_SIZE[0])
        self.ax1.set_ylim(ROOM_SIZE[1])
    
        for EUI in DW1000_DEVICE_CALIB:
            if 'coord' in DW1000_DEVICE_CALIB[EUI]:
                C = DW1000_DEVICE_CALIB[EUI]['coord']
                self.ax1.plot(C[0],C[1],'rx')

        self.p1 = self.ax1.plot([], [], 'o', mfc='#0000C0FF')
        self.p2 = self.ax1.plot([], [], 'o', mfc='#00008010', mec='#00000000', ms=1)
        self.p3 = self.ax1.annotate('', (0,0))

        self.fig.show()

    def update(self,tag,loc,org,dia):
        plt.setp(self.p1, xdata=loc[0])
        plt.setp(self.p1, ydata=loc[1])
        plt.setp(self.p2, xdata=org[0])
        plt.setp(self.p2, ydata=org[1])
        plt.setp(self.p2, ms=dia*300)
        plt.setp(self.p3, text='{0} ({1[0]:.2f},{1[1]:.2f},{1[2]:.2f})'.format(tag,loc))
        plt.setp(self.p3, text='{0} ({1[0]:.2f},{1[1]:.2f})'.format(tag,loc))
        #plt.setp(self.p3, position=(org[0]+dia,org[1]+dia))
        plt.setp(self.p3, position=(org[0]+0.15,org[1]+0.15))
        self.fig.canvas.draw()


def TDOA1(blk, tmr, tag, ref, anc, delay, rawts=False):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32
        
    Tm = tmr.sync()
    
    ia = blk.Blink(tag.addr,Tm)
    Tm = tmr.nap(delay[0])
    ib = blk.Blink(ref.addr,Tm)
    Tm = tmr.nap(delay[1])
    ic = blk.Blink(tag.addr,Tm)

    tss = [ref,] + anc
    
    blk.WaitBlinks((ia,ib,ic),tss,delay[2])

    T2 = blk.getTS(ia, ref.eui, rawts)
    T3 = blk.getTS(ib, ref.eui, rawts)
    T6 = blk.getTS(ic, ref.eui, rawts)

    data = {}
    
    for rem in anc:
        try:
            Jref = GetDistJiffies(ref.eui,rem.eui,SCL)
            
            T1 = blk.getTS(ia, rem.eui, rawts)
            T4 = blk.getTS(ib, rem.eui, rawts)
            T5 = blk.getTS(ic, rem.eui, rawts)
            
            T41 = T4 - T1
            T32 = T3 - T2
            T54 = T5 - T4
            T63 = T6 - T3
            T51 = T5 - T1
            T62 = T6 - T2
            
            Jtot = 2 * (T41*T63 - T32*T54) // (T51+T62)
            Jdoa = Jtot - Jref
            Tdoa = Jdoa / SCL
            Ldoa = Tdoa * C_AIR * 1E-9

            if Ldoa<-10 or Ldoa>10:
                raise ValueError

            data[rem.eui] = { 'anchor': rem, 'host': rem.host, 'LDOA': Ldoa, 'TDOA': Tdoa, }
            
            #eprint(' >>> {}:{} {:.3f}ns {:.3f}m'.format(ref.host,rem.host,Tdoa,Ldoa))
            
        except (KeyError,ValueError,ZeroDivisionError):
            pass
            
    blk.PurgeBlink(ia)
    blk.PurgeBlink(ib)
    blk.PurgeBlink(ic)
    
    return data


def TDOA2(blk, tmr, tag, ref, anc, delay, rawts=False):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32
        
    Tm = tmr.sync()
    
    ia = blk.Blink(ref.addr,Tm)
    Tm = tmr.nap(delay[0])
    ib = blk.Blink(tag.addr,Tm)
    Tm = tmr.nap(delay[1])
    ic = blk.Blink(ref.addr,Tm)

    tss = [ref,] + anc
    
    blk.WaitBlinks((ia,ib,ic),tss,delay[2])

    T1 = blk.getTS(ia, ref.eui, rawts)
    T4 = blk.getTS(ib, ref.eui, rawts)
    T5 = blk.getTS(ic, ref.eui, rawts)

    data = {}
    
    for rem in anc:
        try:
            Jref = GetDistJiffies(ref.eui,rem.eui,SCL)
            
            T2 = blk.getTS(ia, rem.eui, rawts)
            T3 = blk.getTS(ib, rem.eui, rawts)
            T6 = blk.getTS(ic, rem.eui, rawts)
            
            T41 = T4 - T1
            T32 = T3 - T2
            T54 = T5 - T4
            T63 = T6 - T3
            T51 = T5 - T1
            T62 = T6 - T2
            
            Jtot = 2 * (T41*T63 - T32*T54) // (T51+T62)
            Jdoa = Jtot - Jref
            Tdoa = Jdoa / SCL
            Ldoa = Tdoa * C_AIR * 1E-9

            if Ldoa<-25 or Ldoa>25:
                raise ValueError

            data[rem.eui] = { 'anchor': rem, 'host': rem.host, 'LDOA': Ldoa, 'TDOA': Tdoa, }
            
            #eprint(' >>> {}:{} {:.3f}ns {:.3f}m'.format(ref.host,rem.host,Tdoa,Ldoa))
            
        except (KeyError,ValueError,ZeroDivisionError):
            pass
            
    blk.PurgeBlink(ia)
    blk.PurgeBlink(ib)
    blk.PurgeBlink(ic)
    
    return data


def main():
    
    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="OWR delay tool")

    DW1000.AddParserArguments(parser)
    
    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay, help='Delay between blinks')
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait, help='Time to wait timestamp reception')
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT, help='UDP port')
    parser.add_argument('-R', '--raw', action='store_true', default=False, help='Use raw timestamps')
    parser.add_argument('-S', '--sigma', type=float, default=CFG.sigma, help='Sigma')
    parser.add_argument('-A', '--algo', type=str, default=None, help='Algorithm')
    
    parser.add_argument('--delay1', type=float, default=None)
    parser.add_argument('--delay2', type=float, default=None)
    parser.add_argument('remote', type=str, nargs='+', help="Remote addresses")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    DEBUG = args.debug

    if args.algo is None:
        ALGO = TDOA2
    elif args.algo == 'TDOA1' or args.algo == '1':
        ALGO = TDOA1
    elif args.algo == 'TDOA2' or args.algo == '2':
        ALGO = TDOA2
    else:
        ALGO = None

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

    tag = remotes[0]
    ref = remotes[1]
    anc = remotes[2:]

    viz = room()
    tmr = tail.Timer()
    blk = tail.Blinker(rpc,0)

    eprint('Starting...')

    try:
        while True:
            try:
                data = ALGO(blk, tmr, tag, ref, anc, (delay1,delay2,args.wait), rawts=args.raw)

                refxyz = np.array(ref.GetCoord())
                ldiffs = np.array([ meas['LDOA'] for meas in data.values() ])
                coords = np.array([ meas['anchor'].GetCoord() for meas in data.values() ])
                
                X,C = tdoa.hyperlater(refxyz,coords,ldiffs,args.sigma)

                if VERBOSE > 0:
                    eprint('Raw location: {}'.format(X))
                
                Txyz = ( X[0], X[1], 0.0 )
                #Txyz = ( pround(X[0],CFG.round), pround(X[1],CFG.round), 0.0 )
                
                if np.amin(Txyz) > -10 and np.amax(Txyz) < 10:
                    Ewma = min(TAGS['Tcnt'],CFG.ewma)
                    Tcnt = TAGS['Tcnt']
                    Tavg = TAGS['Tavg']
                    Vavg = TAGS['Vavg']
                    Tdif = pround(Txyz-Tavg,CFG.round)
                    Tavg = Tavg + Tdif/Ewma
                    if Tcnt > CFG.ewma:
                        Vavg = Vavg + (tdoa.dsq(Tdif)-Vavg)/Ewma
                    else:
                        Vavg = 0.01
                    Davg = np.sqrt(Vavg)
                    TAGS['Tavg'] = Tavg
                    TAGS['Vavg'] = Vavg
                    TAGS['Tcnt'] = Tcnt + 1
                    viz.update(tag.host,Txyz,Tavg,Davg)
                    print('Tag {0}: ({1[0]:.3f},{1[1]:.3f}) error ~ {2:.3f}m'.format(tag.host,Txyz,Davg))
            
            except (TimeoutError):
                eprint('Tag {}: Timeout'.format(tag.host))
                
            except np.linalg.LinAlgError as err:
                eprint('Tag {}: Lateration failed: {}'.format(tag.host,err))
            
    except KeyboardInterrupt:
        eprint('\nStopping...')
    except Exception as err:
        eprint('\nUnexpected Error: {}'.format(err))
        traceback.print_exc()

    finally:
        blk.stop()
        rpc.stop()


if __name__ == "__main__":
    main()

