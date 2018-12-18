#!/usr/bin/python3
#
# Tx Power calibration for Tail algorithm development
#

import sys
import math
import queue
import socket
import json
import argparse
import threading
import tail

import numpy as np
import numpy.linalg as lin

from tail import *
from config import *


class Config():

    blink_count  = 100
    blink_delay  = 0.010
    blink_wait   = 0.250

    rx_power     = -75.0
    tx_power     = None
    at_power     = None
    
    rawts        = True

    ch           = None
    prf          = None
    freq         = None

    def_attr = {
        'smart_power' : 0,
        'tx_power'    : 0xd1,
        'channel'     : 7,
        'pcode'	      : 20,
        'prf'	      : 64,
        'rate'	      : 850,
        'txpsr'	      : 1024,
    }

    
CFG = Config()

Pi = math.pi
Cs = 299792458

UWB_Ch = ( None, 3494.4E6, 3993.6E6, 4492.8E6, 3993.6E6, 6489.6E6, None, 6489.6E6 )


##
## Functions
##

def RFProp(m,fc,pt):
    return pt - 20*np.log10(m*fc*4*Pi/Cs)


def TxPwr2Reg(txpwr):
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


def Reg2TxPwr(txreg):
    pwr = int(txreg,0)
    if pwr > 0xff:
        pwr = (pwr >> 16) & 0xff
    a = (pwr >> 5) & 0x07
    b = (pwr >> 0) & 0x1f
    return ((6-a)*3,b/2)


def TxPwrNorm(txpwr):
    txp = list(txpwr)
    while txp[0] <= 18.0 and txp[1] > 9.0:
        txp[1] -= 3.0
        txp[0] += 3.0
    while txp[0] >= 3.0 and txp[1] < 3.0:
        txp[1] += 3.0
        txp[0] -= 3.0
    return txp


def XTALT_PPM(blk, tmr, dut, refs, delay, count=1, rawts=False):
    
    Fcnt = 0
    Fsum = 0.0

    for i in range(count):

        tm = tmr.sync()
        i1 = blk.Blink(dut.addr,tm)
        tm = tmr.nap(delay[0])
        i2 = blk.Blink(dut.addr,tm)

        try:
            blk.WaitBlinks((i1,i2),refs,delay[2])
        
        except (TimeoutError):
            veprints(2,'T')

        for dev in refs:
            try:
                T1 = blk.getTS(i1, dut.eui, rawts)
                T2 = blk.getTS(i1, dev.eui, rawts)
                T3 = blk.getTS(i2, dut.eui, rawts)
                T4 = blk.getTS(i2, dev.eui, rawts)
            
                T31 = T3 - T1
                T42 = T4 - T2
            
                Err = (T42 - T31) / T42

                F2 = blk.getXtalPPM(i1, dev.eui)
                F4 = blk.getXtalPPM(i2, dev.eui)
                
                Est = (F2 + F4) / 2
            
                Fcnt += 1
                Fsum += Err
            
            except (KeyError):
                veprints(2,'?')
            except (ValueError):
                veprints(2,'^')
            except (ZeroDivisionError):
                veprints(2,'0')

            else:
                if Fcnt%10==0:
                    veprints(2,'.')
                    
        blk.PurgeBlink(i1)
        blk.PurgeBlink(i2)

    if Fcnt < count/2:
        raise RuntimeError('No XTALT measurements')
    
    Fppm = Fsum/Fcnt
    
    return Fppm


def XTALT_Calib(blk, tmr, dut, refs, delay, rawts=False):
    
    Loop = 10
    Pavg = 0.0
    
    xtalt = int(dut.GetAttr('xtalt'))
    
    veprint(1, 'Calibrating {} <{}> XTALT:'.format(dut.host,dut.eui))
        
    while Loop > 0:
        Loop -= 1
        
        dut.SetAttr('xtalt', xtalt)
        
        Pavg = XTALT_PPM(blk,tmr,dut,refs,delay=delay,count=CFG.blink_count,rawts=rawts)
        Pavg = Pavg * 1E6

        veprint(2)
        veprint(1, 'XTALT:{} {:.3f}ppm '.format(xtalt,Pavg))
            
        if Pavg > 8.0:
            xtalt -= int(Pavg/4)
        elif Pavg > 1.8:
            xtalt -= 1
        elif Pavg < -8.0:
            xtalt -= int(Pavg/4)
        elif Pavg < -1.8:
            xtalt += 1
        else:
            break
        
    veprint(1, 'RESULT: XTALT:{} {:.3f}ppm'.format(xtalt,Pavg))
        
    return (xtalt,Pavg)


def TXPWR_EST(blk, tmr, dut, refs, delay, count=1, txpwr=None, rawts=False):

    Pcnt = 0
    Psum = 0.0
    Fsum = 0.0
    Tsum = 0.0
    Vsum = 0.0

    if txpwr is not None:
        dut.SetAttr('tx_power', TxPwr2Reg(txpwr))
    
    for i in range(count):

        Tm = tmr.sync()
        i1 = blk.Blink(dut.addr,Tm)

        try:
            blk.WaitBlinks((i1,),refs,delay[2])

        except TimeoutError:
            veprints(2,'T')
    
        for dev in refs:
            try:
                Plin = blk.getRxPower(i1,dev.eui)
                Flin = blk.getFpPower(i1,dev.eui)
                Temp = blk.getTemp(i1,dut.eui)
                Volt = blk.getVolt(i1,dut.eui)
            
                Psum += Plin
                Fsum += Flin
                Tsum += Temp
                Vsum += Volt
                Pcnt += 1
            
            except (KeyError):
                veprints(2,'?')
            except (ValueError):
                veprints(2,'^')
            except (ZeroDivisionError):
                veprints(2,'0')

            else:
                if Pcnt%10==0:
                    veprints(2,'.')
                    
        blk.PurgeBlink(i1)
    
    if Pcnt < count/2:
        raise RuntimeError('No TxPower measurements')
    
    Pavg = Plin/Pcnt
    Favg = Flin/Pcnt
    Tavg = Tsum/Pcnt
    Vavg = Vsum/Pcnt
    
    return (Pavg,Favg,Tavg,Vavg)


def TXPWR_Calib(blk, tmr, dut, refs, delay, txpwr=None, rxpwr=None, rawts=False):
    
    tx_pwr = list(txpwr)
    rx_pwr = rxpwr

    Loop = 10

    veprint(1, 'Calibrating {} <{}> TxPWR:'.format(dut.host,dut.eui))
        
    while Loop > 0:
        Loop -= 1

        Pwrs = [ ]
        Fprs = [ ]
        Tmps = [ ]
        Vlts = [ ]

        Tcnt = 0
        
        for i in range(CFG.blink_count):
            try:
                (Pavg,Favg,Temp,Volt) = TXPWR_EST(blk,tmr,dut,refs,delay=delay,txpwr=tx_pwr,rawts=rawts)

                Pwrs.append(Pavg)
                Fprs.append(Favg)
                Tmps.append(Temp)
                Vlts.append(Volt)

                Tcnt += 1

            except RuntimeError:
                veprints(2,'x')

            else:
                if tail.VERBOSE > 2:
                    eprints('\rRx: {:.1f}dBm'.format(DW1000.RxPower2dBm(Pavg,CFG.prf)))
                else:
                    if Tcnt%10==0:
                        veprints(2,'.')
            
        if Tcnt < 10:
            raise RuntimeError('Not enough measurements')

        Pavg = np.mean(Pwrs)
        Pstd = np.std(Pwrs)

        Plog = DW1000.RxPower2dBm(Pavg,CFG.prf)
        Pstl = DW1000.RxPower2dBm(Pavg+Pstd,CFG.prf) - Plog

        Tavg = np.mean(Tmps)
        Tstd = np.std(Tmps)

        if tail.VERBOSE > 2:
            eprint('STATISTICS')
            eprint('    Samples:   {} [{:.1f}%]'.format(Tcnt,(100*Tcnt/CFG.blink_count)-100))
            eprint('    Channel:   {}'.format(CFG.ch))
            eprint('    PRF:       {}'.format(CFG.prf))
            eprint('    Temp:      {:.1f}°C [{:.2f}°C]'.format(Tavg,Tstd))
            eprint('    TxPWR:     {0:+.1f}dBm [{1[0]:.0f}{1[1]:+.1f}]'.format(tx_pwr[0]+tx_pwr[1], tx_pwr))
            eprint('    RxPWR:     {:.1f}dBm [{:.2f}dBm]'.format(Plog,Pstl))
            eprint()
        else:
            veprint(2)
            veprint(1, 'TxPwr: {0[0]:.0f}{0[1]:+.1f}dBm RxPWR:{1:.1f}dBm'.format(tx_pwr,Plog))

            

        ##
        ## Adjust Tx Power
        ##

        delta = Plog - rx_pwr

        fine1 = ( tx_pwr[0] ==  0 and delta > 0 )
        fine2 = ( tx_pwr[0] == 18 and delta < 0 )
        fine3 = ( -1.5 < delta < 1.5 )

        if fine1 or fine2 or fine3:
            
            if -0.3 < delta < 0.3:
                break

            if tx_pwr[1] > 3.0 and delta > 1.0:
                tx_pwr[1] -= 1.0
            
            elif tx_pwr[1] > 0.5 and delta > 0.25:
                tx_pwr[1] -= 0.5
            
            elif tx_pwr[1] < 12.0 and delta < -1.0:
                tx_pwr[1] += 1.0

            elif tx_pwr[1] < 15.0 and delta < -0.25:
                tx_pwr[1] += 0.5

        else:

            if -1.75 < delta < 1.75:
                break
            
            if tx_pwr[0] > 0.0 and delta > 1.5:
                tx_pwr[0] -= 3.0

            elif tx_pwr[0] < 18.0 and delta < -1.5:
                tx_pwr[0] += 3.0

    return (tx_pwr,Plog)


def TWR_EST(blk, tmr, dut, rem, delay, txpwr=None, rawts=False):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32

    if txpwr is not None:
        dut.SetAttr('tx_power', TxPwrs2Reg(txpwr[0]))
        rem.SetAttr('tx_power', TxPwrs2Reg(txpwr[1]))
    
    Tm = tmr.sync()
    i1 = blk.Blink(dut.addr,Tm)
    Tm = tmr.nap(delay[0])
    i2 = blk.Blink(rem.addr,Tm)
    Tm = tmr.nap(delay[1])
    i3 = blk.Blink(dut.addr,Tm)

    blk.WaitBlinks((i1,i2,i3),(dut,rem),delay[2])
    
    T1 = blk.getTS(i1, dut.eui, rawts)
    T2 = blk.getTS(i1, rem.eui, rawts)
    T3 = blk.getTS(i2, rem.eui, rawts)
    T4 = blk.getTS(i2, dut.eui, rawts)
    T5 = blk.getTS(i3, dut.eui, rawts)
    T6 = blk.getTS(i3, rem.eui, rawts)
    
    P1 = blk.getRxPower(i2,dut.eui)
    P2 = blk.getRxPower(i1,rem.eui)
    
    F1 = blk.getFpPower(i2,dut.eui)
    F2 = blk.getFpPower(i1,rem.eui)

    C1 = blk.getTemp(i1,dut.eui)
    C2 = blk.getTemp(i2,rem.eui)
    
    V1 = blk.getVolt(i1,dut.eui)
    V2 = blk.getVolt(i2,rem.eui)
    
    S1 = blk.getSNR(i2,dut.eui)
    S2 = blk.getSNR(i1,rem.eui)
    
    N1 = blk.getNoise(i2,dut.eui)
    N2 = blk.getNoise(i1,rem.eui)
    
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
    
    return (Time, dut.host,rem.host, Dof,Lof, txpwr, PPM, S1,P1,F1,N1,C1,V1, S2,P2,F2,N2,C2,V2)



def main():
    
    global VERBOSE, DEBUG, CFG
    
    parser = argparse.ArgumentParser(description="DW1000 calibratuur")

    DW1000.AddParserArguments(parser)

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-R', '--raw', action='store_true', default=False)
    parser.add_argument('-P', '--power', type=float, default=CFG.rx_power)
    parser.add_argument('-A', '--atten', type=float, default=CFG.at_power)
    
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    tail.VERBOSE = args.verbose
    tail.DEBUG = args.debug

    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait  = args.wait

    rpc = tail.RPC(('', args.port))
    
    devs = [ ]
    refs = [ ]
    duts = [ ]
    
    for host in args.remote:
        star = host.startswith('*') or host.endswith('*')
        host = host.strip('*').rstrip('*')
        anch = DW1000(host,args.port,rpc)
        devs.append(anch)
        if star:
            duts.append(anch)
        else:
            refs.append(anch)
            
    #for rem in devs:
    #    for attr in CFG.def_attr:
    #        rem.SetAttr(attr, CFG.def_attr[attr])
    
    DW1000.HandleArguments(args,devs)

    if tail.VERBOSE > 2:
        DW1000.PrintAllRemoteAttrs(devs)

    tmr = tail.Timer()
    blk = tail.Blinker(rpc,DEBUG)

    CFG.ch = int(duts[0].GetAttr('channel'))
    CFG.prf = int(duts[0].GetAttr('prf'))
    CFG.freq = UWB_Ch[CFG.ch]
    CFG.tx_power = duts[0].GetAttr('tx_power')
    
    rxpwr = args.power
    txpwr = TxPwrNorm(Reg2TxPwr(CFG.tx_power))
    delay = [ CFG.blink_delay, CFG.blink_delay, CFG.blink_wait ]

    try:
        for dut in duts:
            (xtalt,ppm) = XTALT_Calib(blk,tmr,dut,refs,delay,rawts=args.raw)
            
        for dut in duts:
            (txp,rxp) = TXPWR_Calib(blk,tmr,dut,refs,delay,txpwr=txpwr,rxpwr=rxpwr,rawts=args.raw)
            veprint(1, 'RESULT: TxPWR:{0[0]:.0f}{0[1]:+.1f}dBm RxPWR:{1:.1f}dBm'.format(txp,rxp))
    
    except (KeyboardInterrupt):
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    

if __name__ == "__main__":
    main()

