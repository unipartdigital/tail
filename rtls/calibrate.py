#!/usr/bin/python3
#
# Automatic DW1000 calibration for Tail development
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
    
    blink_count    = 100
    blink_delay    = 0.010
    blink_wait     = 0.250

    rawts          = True

    distance       = 10.0

    rx_power       = -75.0
    tx_power       = (None,None)
    
    
CFG = Config()

Pi = math.pi
LIGHT_SPEED = 299792458

UWB_Ch = ( None, 3494.4E6, 3993.6E6, 4492.8E6, 3993.6E6, 6489.6E6, None, 6489.6E6 )

DW1000_CALIB_ATTRS = (
    'channel',
    'prf',
    'pcode',
    'txpsr',
    'rate',
    'smart_power',
    'tx_power',
    'xtalt',
    'antd',
)


##
## Functions
##

def TxPwrPair2Reg(txpwr):
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
    return '{:#02x}'.format(f)


def Reg2TxPwrPair(txreg):
    pwr = int(txreg,0)
    if pwr > 0xff:
        pwr = (pwr >> 16) & 0xff
    a = (pwr >> 5) & 0x07
    b = (pwr >> 0) & 0x1f
    return ((6-a)*3,b/2)


def XTAL_PPM_EST(blk, tmr, dut, refs, delay, count=1, rawts=False):
    
    PPMs = [ ]
    Fcnt = 0

    devs = refs + [dut,]
    
    for i in range(count):

        tm = tmr.sync()
        i1 = blk.Blink(dut,tm)
        tm = tmr.nap(delay[0])
        i2 = blk.Blink(dut,tm)

        try:
            blk.WaitBlinks((i1,i2),devs,delay[2])
        except TimeoutError:
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
                
                Fcnt += 1
                PPMs.append(Err)
            
            except KeyError as Err:
                veprints(2,'?')
            except ValueError as Err:
                veprints(2,'^')
            except ZeroDivisionError as Err:
                veprints(2,'0')

            else:
                if Fcnt%10==0:
                    veprints(2,'.')
        
        blk.PurgeBlink(i1)
        blk.PurgeBlink(i2)

    if Fcnt < count/2:
        raise RuntimeError('XTAL_PPM_EST: Not enough XTALT measurements')
    
    Fppm = np.mean(PPMs)
    Fstd = np.std(PPMs)
    
    return (1E6*Fppm,1E6*Fstd)


def XTALT_CALIB(blk, tmr, dut, refs, delay, rawts=False):
    
    xtalt = int(dut.GetDWAttr('xtalt'))
    
    veprint(1, 'Calibrating {} <{}> XTALT [{}]'.format(dut.host,dut.eui,xtalt))
        
    for loop in range(10):

        dut.SetDWAttr('xtalt', xtalt)
        
        (Pavg,Pstd) = XTAL_PPM_EST(blk,tmr,dut,refs,delay=delay,count=CFG.blink_count,rawts=rawts)
        
        if tail.VERBOSE > 2:
            eprint('\rSTATISTICS [{}]                                '.format(loop))
            eprint('    XTALT:     {}'.format(xtalt))
            eprint('    PPM:       {:+.3f}ppm [{:.3f}ppm]'.format(Pavg,Pstd))
        else:
            veprint(2)
            veprint(1, ' [{}] {} => {:+.3f}ppm '.format(loop,xtalt,Pavg))

        if -100 < Pavg < 100 and Pstd < 10:
        
            if Pavg > 8.0:
                xtalt -= int(Pavg/4)
            elif Pavg > 1.6:
                xtalt -= 1
            elif Pavg < -8.0:
                xtalt -= int(Pavg/4)
            elif Pavg < -1.6:
                xtalt += 1
            else:
                break

            if xtalt < 1:
                xtalt = 1
            if xtalt > 30:
                xtalt = 30

    return (xtalt,Pavg)


def TXPWR_EST(blk, tmr, dut, refs, delay, count=1, rawts=False):

    Pcnt = 0
    Psum = 0.0
    Fsum = 0.0

    Tcnt = 0
    Tsum = 0.0
    Vsum = 0.0

    devs = refs + [dut,]
    
    for i in range(count):

        Tm = tmr.sync()
        i1 = blk.Blink(dut,Tm)

        try:
            blk.WaitBlinks((i1,),devs,delay[2])
        except TimeoutError:
            veprints(2,'T')

        try:
            Temp = blk.getTemp(i1,dut.eui)
            Volt = blk.getVolt(i1,dut.eui)
        
            Tsum += Temp
            Vsum += Volt
            Tcnt += 1

        except KeyError as Err:
            veprints(2,'!')
        except ValueError as Err:
            veprints(2,'-')
            
        for dev in refs:
            try:
                Plin = blk.getRxPower(i1,dev.eui)
                Flin = blk.getFpPower(i1,dev.eui)
            
                Psum += Plin
                Fsum += Flin
                Pcnt += 1
            
            except KeyError as Err:
                veprint(3, '\nTXPWR_EST::KeyError: {}'.format(Err))
                veprints(2,'?')
            except ValueError as Err:
                veprint(3, '\nTXPWR_EST::ValueError: {}'.format(Err))
                veprints(2,'~')

            else:
                if Pcnt%10==0:
                    veprints(2,'.')
                    
        blk.PurgeBlink(i1)
    
    if Pcnt < count/2:
        raise RuntimeError('TXPWR_EST: No TxPower measurements')
    
    Pavg = Psum/Pcnt
    Favg = Fsum/Pcnt
    Tavg = Tsum/Tcnt
    Vavg = Vsum/Tcnt
    
    return (Pavg,Favg,Tavg,Vavg)


def TXPWR_CALIB(blk, tmr, dut, refs, delay, txpwr=None, rxpwr=None, prf=64, rawts=False):
    
    tx_pwr = list(txpwr)
    rx_pwr = rxpwr

    veprint(1, 'Calibrating {} <{}> TxPWR {}'.format(dut.host,dut.eui,tx_pwr))
        
    for loop in range(10):

        Pwrs = [ ]
        Fprs = [ ]
        Tmps = [ ]
        Vlts = [ ]

        Tcnt = 0
        
        dut.SetDWAttr('tx_power', TxPwrPair2Reg(tx_pwr))
    
        for i in range(CFG.blink_count):
            try:
                (Pavg,Favg,Temp,Volt) = TXPWR_EST(blk,tmr,dut,refs,delay=delay,rawts=rawts)

                Pwrs.append(Pavg)
                Fprs.append(Favg)
                
                if -10 < Temp < 90:
                    Tmps.append(Temp)
                if 2.500 < Volt < 3.500:
                    Vlts.append(Volt)

                Tcnt += 1

            except RuntimeError:
                veprints(2,'x')
            except ZeroDivisionError:
                veprints(2,'0')

            else:
                if tail.VERBOSE > 2:
                    eprints('\rRx: {:.1f}dBm'.format(DW1000.RxPower2dBm(Pavg,prf)))
                else:
                    if Tcnt%10==0:
                        veprints(2,'.')
            
        if Tcnt < 10:
            raise RuntimeError('TXPWR_CALIB: Not enough measurements')

        Pavg = np.mean(Pwrs)
        Pstd = np.std(Pwrs)

        Plog = DW1000.RxPower2dBm(Pavg,prf)
        Pstl = DW1000.RxPower2dBm(Pavg+Pstd,prf) - Plog

        Tavg = np.mean(Tmps)
        Tstd = np.std(Tmps)

        if tail.VERBOSE > 2:
            eprint('\rSTATISTICS [{}]                               '.format(loop))
            eprint('    Samples:   {} [{:.1f}%]'.format(Tcnt,(100*Tcnt/CFG.blink_count)-100))
            eprint('    Temp:      {:.1f}°C [{:.2f}°C]'.format(Tavg,Tstd))
            eprint('    TxPWR:     {0:+.1f}dBm [{1[0]:.0f}{1[1]:+.1f}]'.format(tx_pwr[0]+tx_pwr[1], tx_pwr))
            eprint('    RxPWR:     {:.1f}dBm [{:.2f}dBm]'.format(Plog,Pstl))
        else:
            veprint(2)
            veprint(1, ' [{0}] TxPwr: {1[0]:.0f}{1[1]:+.1f}dBm RxPWR:{2:.1f}dBm'.format(loop,tx_pwr,Plog))

        ##
        ## Adjust Tx Power
        ##

        delta = Plog - rx_pwr

        if -0.3 < delta < 0.3:
            break

        if tx_pwr[1] > 2 and delta > 3.0:
            tx_pwr[1] -= 2.0
        elif tx_pwr[1] > 1 and delta > 1.5:
            tx_pwr[1] -= 1.0
        elif tx_pwr[1] > 0 and delta > 0.25:
            tx_pwr[1] -= 0.5
        elif tx_pwr[1] < 14.0 and delta < -3.0:
            tx_pwr[1] += 2.0
        elif tx_pwr[1] < 15.0 and delta < -1.5:
            tx_pwr[1] += 1.0
        elif tx_pwr[1] < 15.5 and delta < -0.25:
            tx_pwr[1] += 0.5
        
        if tx_pwr[1] == 0 or tx_pwr[1] == 15.5:
            break
        
    return (tx_pwr,Plog)


def TWR_EST(blk, tmr, dut, rem, delay, rawts=False):

    if rawts:
        SCL = DW1000_CLOCK_GHZ
    else:
        SCL = 1<<32

    Tm = tmr.sync()
    i1 = blk.Blink(dut,Tm)
    Tm = tmr.nap(delay[0])
    i2 = blk.Blink(rem,Tm)
    Tm = tmr.nap(delay[1])
    i3 = blk.Blink(dut,Tm)

    blk.WaitBlinks((i1,i2,i3),(dut,rem),delay[2])
    
    T1 = blk.getTS(i1, dut.eui, rawts)
    T2 = blk.getTS(i1, rem.eui, rawts)
    T3 = blk.getTS(i2, rem.eui, rawts)
    T4 = blk.getTS(i2, dut.eui, rawts)
    T5 = blk.getTS(i3, dut.eui, rawts)
    T6 = blk.getTS(i3, rem.eui, rawts)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / SCL
    Lof = Dof * LIGHT_SPEED * 1E-9
    
    if Lof < 0 or Lof > 100:
        raise ValueError
    
    blk.PurgeBlink(i1)
    blk.PurgeBlink(i2)
    blk.PurgeBlink(i3)
    
    return (Lof,Dof,Tof)


def TWR_CALIB(blk, tmr, dut, refs, delay, dist, rawts=False):

    antd = int(dut.GetDWAttr('antd'),0)
    corr = 0.0
    
    veprint(1, 'Calibrating {} <{}> ANTD [{:#04x}]'.format(dut.host,dut.eui,antd))

    for loop in range(20):

        current = int(round(antd+corr))
        
        dut.SetDWAttr('antd', current)
        
        Lofs = [ ]
        Tcnt = 0

        for i in range(CFG.blink_count):
            for rem in refs:
                try:
                    (Lof,Dog,Tof) = TWR_EST(blk,tmr,dut,rem,delay=delay,rawts=rawts)
                    Lofs.append(Lof)
                    Tcnt += 1

                except ValueError:
                    veprints(2,'?')
                except RuntimeError:
                    veprints(2,'x')
                except ZeroDivisionError:
                    veprints(2,'0')
                except TimeoutError:
                    veprints(2,'T')

                else:
                    if Tcnt%10==0:
                        veprints(2,'.')
        
        if Tcnt < 10:
            raise RuntimeError('TWR_CALIB: Not enough measurements')

        Lavg = np.mean(Lofs)
        Lstd = np.std(Lofs)

        if tail.VERBOSE > 2:
            eprint('\rSTATISTICS [{}]              '.format(loop))
            eprint('    Samples:   {}'.format(Tcnt))
            eprint('    Dist:      {:.3f}m [{:.3f}m]'.format(Lavg,Lstd))
            eprint('    Corr:      {:+.1f}'.format(corr))
            eprint('    ANTD:      {:#04x}'.format(current))
        else:
            veprint(2)
            veprint(1, ' [{}] Dist: {:.3f}m [{:.3f}] {:+.1f}'.format(loop,Lavg,Lstd,corr))
        
        ##
        ## Adjust ANTD
        ## 

        error = (Lavg - dist) / (LIGHT_SPEED / DW1000_CLOCK_HZ)

        if -0.75 < error < 0.75:
            break
        
        corr += error
        
    return (current,corr)



def main():
    
    global CFG

    blk = None
    rpc = None
    
    parser = argparse.ArgumentParser(description="DW1000 calibraturd")

    for attr in DW1000_CALIB_ATTRS:
        parser.add_argument('--' + attr, type=str, default=None)

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=CFG.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=CFG.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=CFG.blink_wait)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-P', '--power', type=float, default=CFG.rx_power)
    parser.add_argument('-C', '--coarse', type=int, default=None)
    parser.add_argument('-F', '--fine', type=int, default=None)
    parser.add_argument('-L', '--distance', type=float, default=CFG.distance)
    parser.add_argument('-X', '--calib-xtalt', action='store_true', default=False)
    parser.add_argument('-T', '--calib-txpower', action='store_true', default=False)
    parser.add_argument('-A', '--calib-antd', action='store_true', default=False)
    
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    tail.VERBOSE = args.verbose
    tail.DEBUG = args.debug

    CFG.distance = args.distance

    CFG.blink_count = args.count
    CFG.blink_delay = args.delay
    CFG.blink_wait  = args.wait

    for attr in DW1000_CALIB_ATTRS:
        val = getattr(args,attr,None)
        if val is not None:
            setattr(CFG, 'dw1000_'+attr, val)
    
    rpc = tail.RPC()
    
    devs = [ ]
    refs = [ ]
    duts = [ ]
    
    try:
        for host in args.remote:
            try:
                star = host.startswith('*') or host.endswith('*')
                host = host.strip('*').rstrip('*')
                anch = DW1000(host,args.port,rpc)
                devs.append(anch)
                if star:
                    duts.append(anch)
                else:
                    refs.append(anch)
            except:
                raise RuntimeError('Remote host {} not available'.format(host))
        
        for rem in devs:
            for attr in DW1000_CALIB_ATTRS:
                val = getattr(CFG,'dw1000_'+attr,None)
                if val == 'cal':
                    val = rem.GetDWAttrDefault(attr)
                if val is not None:
                    rem.SetDWAttr(attr,val)

        for rem in refs:
            for attr in ('xtalt','antd'):
                rem.SetDWAttr(attr, rem.GetDWAttrDefault(attr))

        if tail.VERBOSE > 1:
            DW1000.PrintAllRemoteAttrs(devs,True)

        tmr = tail.Timer()
        blk = tail.Blinker(rpc)

        prf = int(duts[0].GetDWAttr('prf'))
        
        rxpwr = args.power
        txpwr = list(Reg2TxPwrPair(duts[0].GetDWAttr('tx_power')))

        if args.coarse is not None:
            txpwr[0] = args.coarse
        if args.fine is not None:
            txpwr[1] = args.fine
    
        delay = [ CFG.blink_delay, CFG.blink_delay, CFG.blink_wait ]

        if args.calib_xtalt:
            for dut in duts:
                (xtalt,ppm) = XTALT_CALIB(blk,tmr,dut,refs,delay,rawts=CFG.rawts)
                print('XTALT {:s} {:d}'.format(dut.host,xtalt))
                
        if args.calib_txpower:
            for dut in duts:
                (txp,rxp) = TXPWR_CALIB(blk,tmr,dut,refs,delay,prf=prf,txpwr=txpwr,rxpwr=rxpwr,rawts=CFG.rawts)
                print('TXPWR {:s} {}'.format(dut.host,TxPwrPair2Reg(txp)))
    
        if args.calib_antd:
            for dut in duts:
                (antd,corr) = TWR_CALIB(blk,tmr,dut,refs,delay,CFG.distance,rawts=CFG.rawts)
                print('ANTD {:s} {:#04x}'.format(dut.host,antd))
    
    except KeyboardInterrupt:
        eprint('\rStopping...')
    except RuntimeError as err:
        eprint('\rERROR: {}'.format(err))

    if blk is not None:
        blk.stop()
    if rpc is not None:
        rpc.stop()



if __name__ == "__main__": main() 

