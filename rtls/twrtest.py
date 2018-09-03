#!/usr/bin/python3
#
# TWR for algorithm development
#

import sys
import time
import math
import queue
import socket
import json
import pprint
import argparse
import tail

from tail import DW1000
from tail import eprint, eprints

from config import *


class Config():

    blink_count  = 1000000
    blink_speed  = 1.0
    blink_delay  = 0.010
    blink_wait   = 0.250
    blink_power  = '3+3'

CFG = Config()

VERBOSE = 0
DEBUG = 0


def power2dBm(val):
    loc = val.find('+')
    if loc > 0:
        a = float(val[:loc])
        b = float(val[loc:])
        c = int(a / 3)
        d = int(b * 2)
        if c<0 or c>6:
            raise ValueError
        if int(a) != 3*c:
            raise ValueError
        if d<0 or d>31:
            raise ValueError
        if b != d/2:
            raise ValueError
        return (a,b)
    else:
        raise ValueError
        

def print_csv(file,index,data):
    if file is not None:
        (Time,Host1,Host2,Pwr,Dof,Lof,PPM,S1,P1,F1,N1,S2,P2,F2,N2) = data
        msg  = time.strftime('%Y/%m/%d,%H:%M:%S')
        msg += ',{}'.format(Time)
        msg += ',{}'.format(index)
        msg += ',{}'.format(Host1)
        msg += ',{}'.format(Host2)
        msg += ',{0[0]:.0f},{0[1]:.1f}'.format(power2dBm(Pwr))
        msg += ',{:.3f}'.format(Dof)
        msg += ',{:.3f}'.format(Lof)
        msg += ',{:.3f}'.format(PPM)
        msg += ',{:.2f}'.format(P1)
        msg += ',{:.2f}'.format(F1)
        msg += ',{}'.format(N1)
        msg += ',{:.2f}'.format(P2)
        msg += ',{:.2f}'.format(F2)
        msg += ',{}'.format(N2)
        msg += '\n'
        file.write(msg)


def DECA_TWR(blk, tmr, remote, delay, power=None, rawts=False):

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

    if power is not None:
        rem1.SetAttr('tx_power', power)
        rem2.SetAttr('tx_power', power)
    
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
    
    P1 = DW1000.RxPower2dBm(blk.getRxPower(i1, eui2),64)
    P2 = DW1000.RxPower2dBm(blk.getRxPower(i2, eui1),64)
    F1 = DW1000.RxPower2dBm(blk.getFpPower(i1, eui2),64)
    F2 = DW1000.RxPower2dBm(blk.getFpPower(i2, eui1),64)
    
    N1 = blk.getNoise(i1,eui2)
    S1 = blk.getSNR(i1,eui2)
    N2 = blk.getNoise(i2,eui1)
    S2 = blk.getSNR(i2,eui1)

    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    PPM = 1E6 * (T62 - T51) / T62

    Tof = (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / SCL
    Lof = Dof * C_AIR * 1E-9
    
    if Lof < 0 or Lof > 100:
        raise ValueError
    
    Time = blk.getTime(i1)
    
    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Time,remote[0].host,remote[1].host,power,Dof,Lof,PPM,S1,P1,F1,N1,S2,P2,F2,N2)


def main():
    
    global VERBOSE, DEBUG
    
    parser = argparse.ArgumentParser(description="TWR tool")

    DW1000.AddParserArguments(parser)
    
    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-o', '--output', type=str, default=None, help='Output file')
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count, help='Number of blinks')
    parser.add_argument('-s', '--speed', type=float, default=CFG.blink_speed, help='Blink speed [Hz]')
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay, help='Delay between blinks')
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait, help='Time to wait timestamp reception')
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT, help='UDP port')
    parser.add_argument('-P', '--power', type=str, default=None, help='Tx power levels')
    parser.add_argument('-R', '--raw', action='store_true', default=False, help='Use raw timestamps')
    parser.add_argument('--delay1', type=float, default=None)
    parser.add_argument('--delay2', type=float, default=None)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    DEBUG = args.debug

    algo = DECA_TWR

    if args.output is not None:
        out = open(args.output, 'w')
    else:
        out = None
        
    delay1 = args.delay
    delay2 = args.delay
    if args.delay1 is not None:
        delay1 = args.delay1
    if args.delay2 is not None:
        delay2 = args.delay2

    if args.power is not None:
        powers = args.power.split(',')
    else:
        powers = [ CFG.blink_power ]

    rpc = tail.RPC(('', args.port))

    remotes = [ ]
    for host in args.remote:
        try:
            anchor = DW1000(host,args.port,rpc)
            remotes.append(anchor)
        except:
            eprint('Remote {} exist does not'.format(host))

    DW1000.HandleArguments(args,remotes)

    if VERBOSE > 2:
        DW1000.PrintAllRemoteAttrs(remotes)

    blk = tail.Blinker(rpc, args.debug)
    tmr = tail.Timer()

    eprint('Blinker starting')

    twait = max(0, 1.0/args.speed - delay1 - delay2)
    index = 1

    try:
        while index < args.count:
            for rem1 in remotes:
                for rem2 in remotes:
                    if rem1 != rem2:
                        for pwr in powers:
                            if VERBOSE == 1:
                                eprints('.')
                            if VERBOSE > 1:
                                eprint('Ranging {}:{} @ PWR:{}'.format(rem1.host,rem2.host,pwr))
                            done = False
                            while not done:
                                tmr.nap(twait)
                                try:
                                    data = algo(blk, tmr, (rem1,rem2), (delay1,delay2,args.wait), power=pwr, rawts=args.raw)
                                    print_csv(out,index,data)
                                    index += 1
                                    done = True
                                    if VERBOSE > 1:
                                        (Time,Host1,Host2,Power,Dof,Lof,PPM,S1,P1,F1,N1,S2,P2,F2,N2) = data
                                        eprint('    {:.3f}m {:.3f}ns Clk:{:+.3f}ppm Rx1:{:.1f}dBm:{:.1f}dBm:{} Rx2:{:.1f}dBm:{:.1f}dBm:{}'.format(Lof,Dof,PPM,P1,F1,N1,P2,F2,N2))
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

    blk.stop()
    rpc.stop()

    if out is not None:
        out.close()


if __name__ == "__main__":
    main()

