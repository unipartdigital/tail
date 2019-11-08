#!/usr/bin/python3
#
# Automatic DW1000 calibration
#

import sys
import math
import argparse

import numpy as np

from tail import *
from dwarf import *
from blinks import *


class cfg():

    debug          = 0
    verbose        = 0

    rpc_port       = 8912
    
    blink_count    = 100
    blink_delay    = 0.010
    blink_wait     = 0.250

    distance       = 10.0
    power          = -12.3
    

def dprint(level, *args, **kwargs):
    if cfg.debug >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)

def veprint(level, *args, **kwargs):
    if cfg.verbose >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)

def veprints(level, *args, **kwargs):
    if cfg.verbose >= level:
        print(*args, file=sys.stderr, end='', flush=True, **kwargs)


def estimate_xtal_ppm(blk, dut, refs, count):
    
    PPMs = [ ]
    Fcnt = 0

    devs = refs + [dut,]

    for i in range(count):

        blk.sync()
        i1 = blk.blink(dut)
        
        blk.nap(cfg.blink_delay)
        i2 = blk.blink(dut)

        try:
            blk.wait_blinks((i1,i2),devs,cfg.blink_wait)
        except TimeoutError:
            veprints(2,'T')
        
        for dev in refs:
            try:
                T1 = blk.get_rawts(i1, dut)
                T2 = blk.get_rawts(i1, dev)
                T3 = blk.get_rawts(i2, dut)
                T4 = blk.get_rawts(i2, dev)
            
                T31 = T3 - T1
                T42 = T4 - T2
            
                Err = (T42 - T31) / T42

                if -100 < Err*1E6 < 100:
                    Fcnt += 1
                    PPMs.append(Err)
            
            except IndexError as err:
                veprints(2,err)
            except KeyError:
                veprints(2,'?')
            except ValueError:
                veprints(2,'^')
            except ZeroDivisionError:
                veprints(2,'0')

            else:
                if Fcnt%10 == 0:
                    veprints(2,'.')
        
        blk.purge_blink(i1)
        blk.purge_blink(i2)

    if Fcnt < count/2:
        raise RuntimeError('estimate_xtal_ppm: Not enough measurements')
    
    Fppm = np.mean(PPMs) * 1E6
    Fstd = np.std(PPMs) * 1E6
    
    return (Fppm,Fstd)


def calibrate_xtalt(blk, dut, refs):
    
    xtalt = int(dut.get_dw1000_attr('xtalt'))
    
    best_xtalt = 17
    best_error = 1000
    
    veprint(1, 'Calibrating {} <{}> XTALT [{}]'.format(dut.name,dut.eui,xtalt))
        
    for loop in range(10):

        dut.set_dw1000_attr('xtalt', xtalt)
        
        (Pavg,Pstd) = estimate_xtal_ppm(blk,dut,refs,count=cfg.blink_count)

        Pavg += cfg.ppm_offset
        
        if cfg.verbose > 2:
            eprint(f'\rSTATISTICS [{loop}]                                ')
            eprint(f'    XTALT:     {xtalt}')
            eprint(f'    PPM:       {Pavg:+.3f}ppm [{Pstd:.3f}ppm]')
        else:
            veprint(2)
            veprint(1, f' [{loop}] {xtalt} => {Pavg:+.3f}ppm ')

        if -100 < Pavg < 100 and Pstd < 10:

            if math.fabs(Pavg) < best_error:
                best_error = math.fabs(Pavg)
                best_xtalt = xtalt
            
            if Pavg > 8.0:
                xtalt -= int(Pavg/4)
            elif Pavg > 1.0:
                xtalt -= 1
            elif Pavg < -8.0:
                xtalt -= int(Pavg/4)
            elif Pavg < -1.0:
                xtalt += 1
            elif -1.0 < Pavg < 1.0:
                break

            if xtalt < 1:
                xtalt = 1
            if xtalt > 30:
                xtalt = 30

    dut.set_dw1000_attr('xtalt', best_xtalt)
    
    return (best_xtalt,Pavg)


def estimate_txpower(blk, dut, refs, count):

    Pcnt = 0
    Psum = 0.0
    Fsum = 0.0

    Tcnt = 0
    Tsum = 0.0
    Vsum = 0.0

    devs = refs + [dut,]
    
    for i in range(count):

        blk.sync()
        i1 = blk.blink(dut)

        try:
            blk.wait_blinks((i1,),devs,cfg.blink_wait)
        except TimeoutError:
            veprints(2,'T')

        try:
            Temp = blk.get_temp(i1,dut)
            Volt = blk.get_volt(i1,dut)
        
            Tsum += Temp
            Vsum += Volt
            Tcnt += 1

        except IndexError as err:
            veprints(2,err)
        except KeyError:
            veprints(2,'!')
        except ValueError:
            veprints(2,'*')
        except ZeroDivisionError:
            veprints(2,'0')
            
        for dev in refs:
            try:
                Plin = blk.get_rx_level(i1,dev)
                Flin = blk.get_fp_level(i1,dev)
            
                Psum += Plin
                Fsum += Flin
                Pcnt += 1
            
            except IndexError as err:
                veprints(2,err)
            except KeyError as Err:
                veprints(2,'?')
            except ValueError as Err:
                veprints(2,'^')
            except ZeroDivisionError:
                veprints(2,'0')

            else:
                if Pcnt%10==0:
                    veprints(2,'.')
                    
        blk.purge_blink(i1)
    
    if Pcnt < count/2:
        raise RuntimeError('estimate_txpower: Not enough measurements')
    
    Pavg = Psum/Pcnt
    Favg = Fsum/Pcnt
    Tavg = Tsum/Tcnt
    Vavg = Vsum/Tcnt
    
    return (Pavg,Favg,Tavg,Vavg)


def calibrate_txpower(blk, dut, refs, txpwr, rxpwr):
    
    tx_pwr = txpwr
    rx_pwr = rxpwr

    veprint(1, 'Calibrating {} <{}> TxPWR {}'.format(dut.host,dut.eui,tx_pwr))

    best_power = [0,0]
    best_error = 1000

    for loop in range(10):

        Pwrs = [ ]
        Fprs = [ ]
        Tmps = [ ]

        Tcnt = 0
        
        dut.set_dw1000_attr('tx_power', TxPwrPair2Reg(tx_pwr))
    
        for i in range(cfg.blink_count):
            try:
                (Pavg,Favg,Temp,Volt) = estimate_txpower(blk,dut,refs)

                Pwrs.append(Pavg)
                Fprs.append(Favg)
                Tmps.append(Temp)
                Tcnt += 1

            except RuntimeError:
                veprints(2,'R')

            else:
                if cfg.verbose > 2:
                    eprints('\rRx: {:.1f}dBm'.format(RxPower2dBm(Pavg,cfg.prf)))
                else:
                    if Tcnt%10==0:
                        veprints(2,'.')
            
        if Tcnt < 10:
            raise RuntimeError('calibrate_txpower: Not enough measurements')

        Pavg = np.mean(Pwrs)
        Pstd = np.std(Pwrs)

        Plog = DW1000.RxPower2dBm(Pavg,prf)
        Pstl = DW1000.RxPower2dBm(Pavg+Pstd,prf) - Plog

        Tavg = np.mean(Tmps)
        Tstd = np.std(Tmps)

        rate = (100*Tcnt/cfg.blink_count)-100

        if cfg.verbose > 2:
            eprint(f'\rSTATISTICS [{loop}]                               ')
            eprint(f'    Samples:   {Tcnt} [{rate:.1f}%]')
            eprint(f'    Temp:      {Tavg:.1f}°C [{Tstd:.2f}°C]')
            eprint(f'    TxPWR:     [{tx_pwr[0]:.0f}:{tx_pwr[1]:+.1f}]')
            eprint(f'    RxPWR:     {Plog:.1f}dBm [{Pstl:.2f}dBm]')
        else:
            veprint(2)
            veprint(1, f' [{loop}] TxPwr: {tx_pwr[0]:.0f}{tx_pwr[1]:+.1f}dBm RxPWR:{Plog:.1f}dBm')

        ##
        ## Adjust Tx Power
        ##

        error = Plog - rx_pwr

        if math.fabs(error) < best_error:
            best_error = math.fabs(error)
            best_power = tx_pwr

        if -0.2 < error < 0.2:
            break

        if tx_pwr[1] > 2 and error > 3.0:
            tx_pwr[1] -= 2.0
        elif tx_pwr[1] > 1 and error > 1.5:
            tx_pwr[1] -= 1.0
        elif tx_pwr[1] > 0 and error > 0.2:
            tx_pwr[1] -= 0.5

        elif tx_pwr[1] < 14.0 and error < -3.0:
            tx_pwr[1] += 2.0
        elif tx_pwr[1] < 15.0 and error < -1.5:
            tx_pwr[1] += 1.0
        elif tx_pwr[1] < 15.5 and error < -0.2:
            tx_pwr[1] += 0.5
        
        if tx_pwr[1] == 0 or tx_pwr[1] == 15.5:
            break
        
    dut.set_dw1000_attr('tx_power', DW1000.tx_power_list_to_code(best_power))
    
    return (best_power,Plog)


def ranging(blk, dut, rem):

    blk.sync()
    i1 = blk.blink(dut)
    blk.nap(cfg.blink_delay)
    i2 = blk.blink(rem)
    blk.nap(cfg.blink_delay)
    i3 = blk.blink(dut)

    try:
        blk.wait_blinks((i1,i2,i3),(dut,rem),cfg.blink_wait)
    except TimeoutError:
        veprints(2,'T')
        
    T1 = blk.get_rawts(i1, dut)
    T2 = blk.get_rawts(i1, rem)
    T3 = blk.get_rawts(i2, rem)
    T4 = blk.get_rawts(i2, dut)
    T5 = blk.get_rawts(i3, dut)
    T6 = blk.get_rawts(i3, rem)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / DW1000_CLOCK_HZ
    Lof = Dof * Cabs
    
    if Lof < -1 or Lof > 100:
        raise ValueError
    
    blk.purge_blink(i1)
    blk.purge_blink(i2)
    blk.purge_blink(i3)
    
    return (Lof,Dof,Tof)


def calibrate_antd(blk, dut, refs, dist):

    antd = int(dut.get_dw1000_attr('antd'),0)
    corr = 0.0
    
    veprint(1, 'Calibrating {} <{}> ANTD [{:#04x}]'.format(dut.host,dut.eui,antd))

    for loop in range(20):

        current = int(round(antd+corr))
        
        dut.set_dw1000_attr('antd', current)
        
        Lofs = [ ]
        Tcnt = 0

        for i in range(cfg.blink_count):
            for rem in refs:
                try:
                    (Lof,Dog,Tof) = ranging(blk,dut,rem)
                    Lofs.append(Lof)
                    Tcnt += 1

                except IndexError as err:
                    veprints(2,err)
                except KeyError:
                    veprints(2,'!')
                except ValueError:
                    veprints(2,'*')
                except TimeoutError:
                    veprints(2,'T')
                except RuntimeError:
                    veprints(2,'R')
                except ZeroDivisionError:
                    veprints(2,'0')

                else:
                    if Tcnt%10==0:
                        veprints(2,'.')
        
        if Tcnt < 10:
            raise RuntimeError('calibrate_antd: Not enough measurements')

        Lavg = np.mean(Lofs)
        Lstd = np.std(Lofs)

        if cfg.verbose > 2:
            print(f'\rSTATISTICS [{loop}]              ')
            print(f'    Samples:   {Tcnt}')
            print(f'    Dist:      {Lavg:.3f}m [{Lstd:.3f}m]')
            print(f'    Corr:      {corr:+.1f}')
            print(f'    ANTD:      {current:#04x}')
        else:
            veprint(2)
            veprint(1, f' [{loop}] Dist: {Lavg:.3f}m [{Lstd:.3f}] {corr:+.1f}')
        
        ##
        ## Adjust ANTD
        ## 

        error = (Lavg - dist) / (Cabs / DW1000_CLOCK_HZ)

        if -0.75 < error < 0.75:
            break
        
        corr += error
        
    return (current,corr)



def main():
    
    parser = argparse.ArgumentParser(description="DW1000 calibraturd")

    DW1000.add_device_arguments(parser)
    
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=cfg.blink_wait)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('-O', '--ppm-offset', type=float, default=0.0)
    parser.add_argument('-P', '--power', type=float, default=cfg.power)
    parser.add_argument('-C', '--coarse', type=int, default=None)
    parser.add_argument('-F', '--fine', type=int, default=None)
    parser.add_argument('-L', '--distance', type=float, default=cfg.distance)
    parser.add_argument('-X', '--calib-xtalt', action='store_true', default=False)
    parser.add_argument('-T', '--calib-txpower', action='store_true', default=False)
    parser.add_argument('-A', '--calib-antd', action='store_true', default=False)
    
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    cfg.debug = args.debug
    cfg.verbose = args.verbose
    WPANFrame.verbosity = args.verbose

    cfg.blink_count = args.count
    cfg.blink_delay = args.delay
    cfg.blink_wait  = args.wait
    
    cfg.ppm_offset = args.ppm_offset
    
    cfg.channel = int(args.channel)
    cfg.prf = int(args.prf)
    
    cfg.power = args.power
    cfg.distance = args.distance
    
    cfg.rx_power = RFCalcRxPower(cfg.channel, cfg.distance, cfg.power)
    

    ##
    ## Devices
    ##
    
    rpc = RPC()
    
    devs = [ ]
    refs = [ ]
    duts = [ ]
    
    for host in args.remote:
        try:
            star = host.startswith('*') or host.endswith('*')
            host = host.strip('*').rstrip('*')
            name = host.split('.')[0]
            adev = DW1000(rpc,name,host,args.port)
            adev.connect()
            devs.append(adev)
            if star:
                duts.append(adev)
            else:
                refs.append(adev)

        except (ValueError,ConnectionError) as err:
            raise RuntimeError(f'Remote host {host} not available: {err}')
    
    DW1000.handle_device_arguments(args,devs)
    
    if args.verbose > 0:
        DW1000.print_all_remote_attrs(devs,True)
        

    ##
    ## Calibrator
    ##
    
    blk = Blinks(rpc)

    rxpwr = cfg.rx_power
    txpwr = DW1000.tx_power_reg_to_list( duts[0].get_dw1000_attr('tx_power') )

    if args.coarse is not None:
        txpwr[0] = args.coarse
    if args.fine is not None:
        txpwr[1] = args.fine

    try:
        if args.calib_xtalt:
            for dut in duts:
                (xtalt,ppm) = calibrate_xtalt(blk,dut,refs)
                print('XTALT,{:s},{:d}'.format(dut.name,xtalt))
                
        if args.calib_txpower:
            for dut in duts:
                (txp,rxp) = calibrate_txpower(blk,dut,refs,txpwr=txpwr,rxpwr=rxpwr)
                print('TXPWR,{0:s},{1:},{2[0]:},{2[1]:}'.format(dut.name,DW1000.tx_power_list_to_code(txp),txp))
    
        if args.calib_antd:
            for dut in duts:
                (antd,corr) = calibrate_antd(blk,dut,refs,cfg.distance)
                print('ANTD,{:s},{:#04x}'.format(dut.name,antd))
    
    except KeyboardInterrupt:
        eprint('\rStopping...')
    except RuntimeError as err:
        errhandler('Runtime error', err)

    blk.stop()
    rpc.stop()


if __name__ == "__main__": main() 

