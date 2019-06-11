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

    blink_count  = 100000000
    blink_speed  = 1.0
    blink_delay  = 0.010
    blink_wait   = 0.250

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


def print_data(data):
    (Time,Host1,Host2,Pwr,Dof,Lof,PPM,S1,P1,F1,N1,C1,V1,S2,P2,F2,N2,C2,V2) = data
    msg = '   '
    msg += ' {:.3f}m'.format(Lof)
    msg += ' {:.3f}ns'.format(Dof)
    msg += ' Clk:{:+.3f}ppm'.format(PPM)
    msg += ' PWR:{:.1f}dBm:{:.1f}dBm'.format(DW1000.RxPower2dBm(P1),DW1000.RxPower2dBm(P2))
    msg += ' FPR:{:.1f}dBm:{:.1f}dBm'.format(DW1000.RxPower2dBm(F1),DW1000.RxPower2dBm(F2))
    msg += ' Noise:{}:{}'.format(N1,N2)
    msg += ' Temp:{:.2f}C:{:.2f}C'.format(C1,C2)
    msg += ' Volt:{:.3f}V:{:.3f}V'.format(V1,V2)
    eprint(msg)


def print_csv(file,index,data):
    if file is not None:
        (Time,Host1,Host2,Pwr,Dof,Lof,PPM,S1,P1,F1,N1,C1,V1,S2,P2,F2,N2,C2,V2) = data
        (Tx1,Tx2) = power2dBm(Pwr)
        msg  = time.strftime('%Y/%m/%d,%H:%M:%S')		# 0,1
        msg += ',{}'.format(Time)				# 2
        msg += ',{}'.format(index)				# 3
        msg += ',{}'.format(Host1)				# 4
        msg += ',{}'.format(Host2)				# 5
        msg += ',{:.0f}'.format(Tx1)				# 6
        msg += ',{:.1f}'.format(Tx2)				# 7
        msg += ',{:.1f}'.format(Tx1+Tx2)			# 8
        msg += ',{:.3f}'.format(Dof)				# 9
        msg += ',{:.3f}'.format(Lof)				# 10
        msg += ',{:.3f}'.format(PPM)				# 11
        msg += ',{:.2f}'.format(P1)				# 12
        msg += ',{:.2f}'.format(DW1000.RxPower2dBm(P1))		# 13
        msg += ',{:.2f}'.format(F1)				# 14
        msg += ',{:.2f}'.format(DW1000.RxPower2dBm(F1))		# 15
        msg += ',{:.0f}'.format(N1)				# 16
        msg += ',{:.2f}'.format(C1)				# 17
        msg += ',{:.3f}'.format(V1)				# 18
        msg += ',{:.2f}'.format(P2)				# 19
        msg += ',{:.2f}'.format(DW1000.RxPower2dBm(P2))		# 20
        msg += ',{:.2f}'.format(F2)				# 21
        msg += ',{:.2f}'.format(DW1000.RxPower2dBm(F2))		# 22
        msg += ',{:.0f}'.format(N2)				# 23
        msg += ',{:.2f}'.format(C2)				# 24
        msg += ',{:.3f}'.format(V2)				# 25
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
        rem1.SetDWAttr('tx_power', power)
        rem2.SetDWAttr('tx_power', power)
    
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
    V1 = blk.getVolt(i1,eui1)
    C2 = blk.getTemp(i2,eui2)
    V2 = blk.getVolt(i2,eui2)

    N1 = blk.getNoise(i2,eui1)
    S1 = blk.getSNR(i2,eui1)
    N2 = blk.getNoise(i1,eui2)
    S2 = blk.getSNR(i1,eui2)
    
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
    
    return (Time,remote[0].host,remote[1].host,power,Dof,Lof,PPM,S1,P1,F1,N1,C1,V1,S2,P2,F2,N2,C2,V2)


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
    parser.add_argument('-P', '--sweep', type=str, default=None, help='Tx power levels')
    parser.add_argument('-R', '--raw', action='store_true', default=False, help='Use raw timestamps')
    parser.add_argument('--delay1', type=float, default=None)
    parser.add_argument('--delay2', type=float, default=None)
    parser.add_argument('remote', type=str, nargs='+', help="Remote addresses")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    DEBUG = args.debug

    algo = DECA_TWR

    if args.output is not None:
        out = open(args.output, 'w')
    else:
        out = None
        
    if args.sweep is not None:
        powers = args.sweep.split(',')
    else:
        powers = [ None ]

    delay1 = args.delay
    delay2 = args.delay
    if args.delay1 is not None:
        delay1 = args.delay1
    if args.delay2 is not None:
        delay2 = args.delay2

    rpc = tail.RPC(('', args.port))

    anchors = { }
    remotes = [ ]
    
    for hosts in args.remote:
        (host1,host2) = hosts.split(':')
        try:
            if host1 not in anchors:
                anchors[host1] = DW1000(host1,args.port,rpc)
            if host2 not in anchors:
                anchors[host2] = DW1000(host2,args.port,rpc)
            remotes.append((anchors[host1],anchors[host2]))
        except:
            eprint('Remote {} exist does not'.format(hosts))

    DW1000.HandleArguments(args,anchors.values())

    if VERBOSE > 2:
        DW1000.PrintAllRemoteAttrs(anchors.values())

    blk = tail.Blinker(rpc, args.debug)
    tmr = tail.Timer()

    eprint('Blinker starting')

    twait = max(0, 1.0/args.speed - delay1 - delay2 - delay1)
    index = 1
    count = 1

    try:
        while count < args.count:
            count += 1

            for (rem1,rem2) in remotes:
                for pwr in powers:
                    
                    if VERBOSE == 1:
                        eprints('.')
                    if VERBOSE > 1:
                        eprint('Ranging {}:{} @ PWR:{}'.format(rem1.host,rem2.host,pwr))
                        
                    tmr.nap(twait)
                    
                    try:
                        data = algo(blk, tmr, (rem1,rem2), (delay1,delay2,args.wait), power=pwr, rawts=args.raw)
                    
                        if VERBOSE > 1:
                            print_data(data)
                                
                        print_csv(out,index,data)
                        index += 1
                                
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

