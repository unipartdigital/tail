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

from numpy import dot, sin, cos


class cfg():

    debug           = 0
    verbose         = 0

    dw1000_profile  = None
    dw1000_channel  = 5
    dw1000_pcode    = 12
    dw1000_prf      = 64
    dw1000_rate     = 850
    dw1000_txpsr    = 1024
    dw1000_smart    = 0
    dw1000_power    = '0x88888888'

    blink_count     = 100
    blink_delay     = 0.050
    blink_wait      = 0.500
    blink_interval  = 0.250

    distance        = 5.04
    txlevel         = -12.3
    ppm_offset      = 0.0

    rpc_port        = 9812
    
    config_json     = '/etc/calibrator.json'

    def setarg(name, value):
        if value is not None:
            setattr(cfg, name, value)


def dprint(level, *args, **kwargs):
    if cfg.debug >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)

def veprint(level, *args, **kwargs):
    if cfg.verbose >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)

def veprints(level, *args, **kwargs):
    if cfg.verbose >= level:
        print(*args, file=sys.stderr, end='', flush=True, **kwargs)


def estimate_xtal_ppm(blk, dut, refs):
    
    Errs = [ ]
    Volts = [ ]
    Temps = [ ]

    devs = refs + [dut,]

    for i in range(cfg.blink_count):
        try:

            blk.sync(cfg.blink_interval)
            
            i1 = blk.blink(dut)
            blk.nap(cfg.blink_delay)
            i2 = blk.blink(dut)
            
            blk.wait_blinks((i1,i2),devs,cfg.blink_wait)
            
            Temp = blk.get_temp(i1,dut)
            Volt = blk.get_volt(i1,dut)

            Volts.append(Volt)
            Temps.append(Temp)

            for dev in refs:
                try:
                    T1 = blk.get_rawts(i1, dut)
                    T2 = blk.get_rawts(i1, dev)
                    T3 = blk.get_rawts(i2, dut)
                    T4 = blk.get_rawts(i2, dev)
                    
                    T31 = T3 - T1
                    T42 = T4 - T2
                    
                    Err = (T42 - T31) / T42 * 1E6
                    
                    if Err < -100 or Err > 100:
                        raise ValueError

                    Errs.append(Err)

                except KeyError:
                    veprints(2,'?')
                except ValueError:
                    veprints(2,'!')
            
            blk.purge_blink(i1)
            blk.purge_blink(i2)

        except KeyError:
            veprints(2,'?')
        except ValueError:
            veprints(2,'!')
        except ZeroDivisionError:
            veprints(2,'0')
        else:
            veprints(2,'.')
            
    veprint(2)
            
    if len(Errs) < cfg.blink_count/2:
        raise RuntimeError('estimate_xtal_ppm: Not enough measurements')
    
    Eavg = np.mean(Errs)
    Estd = np.std(Errs)
    
    Tavg = np.mean(Temps)
    Tstd = np.std(Temps)
    
    Vavg = np.mean(Volts)
    Vstd = np.std(Volts)

    Tcnt = len(Temps)
    Rate = Tcnt / cfg.blink_count
    
    return (Tcnt,Rate,Eavg,Estd,Tavg,Tstd,Vavg,Vstd)


def calibrate_xtalt(blk, dut, refs):
    
    veprint(1, 'Calibrating {} <{}> XTALT'.format(dut.name,dut.eui))

    TL = 0
    TH = 31

    trims = [ None ] * 32
    
    for loop in range(10):

        if TH - TL == 1:
            if trims[TL] and trims[TH]:
                if trims[TL] < 0.0 and trims[TH] > 0.0:
                    if abs(trims[TL]) < abs(trims[TH]):
                        best = TL
                    else:
                        best = TH
                    break
        
        xtalt = (TH + TL) // 2

        dut.set_dw1000_attr('xtalt', xtalt)
        
        (Tcnt,Rate,Eavg,Estd,Tavg,Tstd,Vavg,Vstd) = estimate_xtal_ppm(blk,dut,refs)

        Eavg += cfg.ppm_offset
        fail = 100 * (1.0 - Rate)

        trims[xtalt] = Eavg

        if cfg.verbose > 2:
            eprint(f'STATISTICS [{loop}] [{TL}:{TH}]')
            eprint(f'    Samples:   {Tcnt} [{fail:.1f}%]')
            eprint(f'    XTALT:     {xtalt}')
            eprint(f'    PPM:       {Eavg:+.3f}ppm [{Estd:.3f}ppm]')
            eprint(f'    Temp:      {Tavg:.1f}°C [{Tstd:.2f}°C]')
            eprint(f'    Volt:      {Vavg:.3f}V [{Vstd:.3f}V]')
        else:
            veprint(1, f' [{loop}] {xtalt} => {Eavg:+.3f}ppm ')

        if -100 < Eavg < 100 and Estd < 10:
            if Eavg < 0.0:
                TL = xtalt
            else:
                TH = xtalt
    
    dut.set_dw1000_attr('xtalt', best)
    
    return best


def estimate_txpower(blk, dut, refs):

    Power = [ ]
    Fpath = [ ]
    Volts = [ ]
    Temps = [ ]
            
    devs = refs + [dut,]
    
    for i in range(cfg.blink_count):
        try:
            
            blk.sync(cfg.blink_interval)
            i1 = blk.blink(dut)

            blk.wait_blinks((i1,),devs,cfg.blink_wait)

            Temp = blk.get_temp(i1,dut)
            Volt = blk.get_volt(i1,dut)

            Volts.append(Volt)
            Temps.append(Temp)

            for dev in refs:
                try:
                    Plin = blk.get_rx_level(i1,dev)
                    Flin = blk.get_fp_level(i1,dev)

                    if Plin and Flin:
                        Power.append(Plin)
                        Fpath.append(Flin)
                    
                except KeyError:
                    veprints(2,'?')
                except ValueError:
                    veprints(2,'!')
            
            blk.purge_blink(i1)
            
        except KeyError:
            veprints(2,'?')
        except ValueError:
            veprints(2,'!')
        except ZeroDivisionError:
            veprints(2,'0')
        else:
            veprints(2,'.')
        
    veprint(2)
    
    if len(Power) < cfg.blink_count:
        raise RuntimeError('estimate_txpower: Not enough measurements')
    
    Pavg = np.mean(Power)
    Pstd = np.std(Power)
    Plog = RxPower2dBm(Pavg,cfg.dw1000_prf)
    Pstl = RxPower2dBm(Pavg+Pstd,cfg.dw1000_prf) - Plog
    
    Favg = np.mean(Fpath)
    Fstd = np.std(Fpath)
    Flog = RxPower2dBm(Favg,cfg.dw1000_prf)
    Fstl = RxPower2dBm(Favg+Fstd,cfg.dw1000_prf) - Flog
    
    Tavg = np.mean(Temps)
    Tstd = np.std(Temps)
    
    Vavg = np.mean(Volts)
    Vstd = np.std(Volts)

    Tcnt = len(Temps)
    Rate = Tcnt / cfg.blink_count
    
    return (Tcnt,Rate,Plog,Pstl,Flog,Fstl,Tavg,Tstd,Vavg,Vstd)


def calibrate_txpower(blk, dut, refs, txpwr, rxpwr):

    veprint(1, 'Calibrating {} <{}> Initial TxPWR:{} Target RxPWR:{:.1f}dBm'.format(dut.name,dut.eui,txpwr,rxpwr))

    TL = 0
    TH = 31

    errors = [ None ] * 32

    for loop in range(10):

        if TH - TL == 1:
            if errors[TL] and errors[TH]:
                if errors[TL] < 0.0 and errors[TH] > 0.0:
                    if abs(errors[TL]) < abs(errors[TH]):
                        txpwr[1] = TL / 2
                    else:
                        txpwr[1] = TH / 2
                    break
        
        TX = (TH + TL) // 2
        txpwr[1] = TX / 2

        dut.set_dw1000_attr('tx_power', DW1000.tx_power_list_to_code(txpwr))

        (Tcnt,Rate,Plog,Pstl,Flog,Fstl,Tavg,Tstd,Vavg,Vstd) = estimate_txpower(blk, dut, refs)

        fail = 100 * (1.0 - Rate)

        if cfg.verbose > 2:
            eprint(f'STATISTICS [{loop}] [{TL}:{TX}:{TH}]')
            eprint(f'    Samples:   {Tcnt} [{fail:.1f}%]')
            eprint(f'    Temp:      {Tavg:.1f}°C [{Tstd:.2f}°C]')
            eprint(f'    Volt:      {Vavg:.3f}V [{Vstd:.3f}V]')
            eprint(f'    TxPWR:     [{txpwr[0]:.0f}{txpwr[1]:+.1f}]')
            eprint(f'    RxPWR:     {Plog:.1f}dBm [{Pstl:.2f}dBm]')
            eprint(f'    FpPWR:     {Flog:.1f}dBm [{Fstl:.2f}dBm]')
        else:
            veprint(1, f' [{loop}] TxPwr: {txpwr[0]:.0f}{txpwr[1]:+.1f}dBm RxPWR:{Plog:.1f}dBm FpPWR:{Flog:.1f}dBm')

        errors[TX] = Perr = Plog - rxpwr

        if -20 < Perr < 20 and Pstl < 10.0:
            if Perr < 0.0:
                TL = TX
            else:
                TH = TX

    dut.set_dw1000_attr('tx_power', DW1000.tx_power_list_to_code(txpwr))
    
    return txpwr


def ranging(blk, dut, rem):

    blk.sync(cfg.blink_interval)
    
    i1 = blk.blink(dut)
    blk.nap(cfg.blink_delay)
    i2 = blk.blink(rem)
    blk.nap(cfg.blink_delay)
    i3 = blk.blink(dut)

    blk.wait_blinks((i1,i2,i3),(dut,rem),cfg.blink_wait)
    
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

    Loe = dut.distance_to(rem)

    Err = Lof - Loe
    
    if Err < -10 or Err > 10:
        raise ValueError(f'Ranging: Err out of bounds: {Err}')
    
    blk.purge_blink(i1)
    blk.purge_blink(i2)
    blk.purge_blink(i3)
    
    return Err


def tringing(blk, dut, dtx, drx):

    blk.sync(cfg.blink_interval)
    
    i1 = blk.blink(dtx)
    blk.nap(cfg.blink_delay)
    i2 = blk.blink(dut)
    blk.nap(cfg.blink_delay)
    i3 = blk.blink(dtx)

    blk.wait_blinks((i1,i2,i3),(dut,dtx,drx),cfg.blink_wait)
    
    T1 = blk.get_rawts(i1, drx)
    T2 = blk.get_rawts(i1, dut)
    T3 = blk.get_rawts(i2, dut)
    T4 = blk.get_rawts(i2, drx)
    T5 = blk.get_rawts(i3, drx)
    T6 = blk.get_rawts(i3, dut)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = 2 * (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / DW1000_CLOCK_HZ
    Lof = Dof * Cabs

    D1 = dtx.distance_to(drx)
    D2 = dtx.distance_to(dut)
    D3 = dut.distance_to(drx)
    
    Loe = D3 + (D2 - D1)
    Err = Lof - Loe

    veprint(4, f'\rDUT:{dut.name} DTX:{dtx.name} DRX:{drx.name} DUTTX:{D1:.3f} DTXRX:{D2:.3f} DUTRX:{D3:.3f} Loe:{Loe:.3f} Lof:{Lof:.3f} Err:{Err:.3f}')

    if Err < -10 or Err > 10:
        raise ValueError(f'Tringing: Err out of bounds: {Err}')
    
    blk.purge_blink(i1)
    blk.purge_blink(i2)
    blk.purge_blink(i3)
    
    return Err


def calibrate_antd(blk, dut, grps):

    antd = int(dut.get_dw1000_attr('antd'),0)
    corr = 0.0
    
    veprint(1, 'Calibrating {} <{}> ANTD [{:#04x}]'.format(dut.name,dut.eui,antd))

    for loop in range(10):

        current = int(round(antd+corr))
        
        dut.set_dw1000_attr('antd', current)
        
        Errs = [ ]

        for i in range(cfg.blink_count):
            for drx in grps[1]:
                for dtx in grps[2]:
                    try:
                        Err = tringing(blk,dut,dtx,drx)
                        Errs.append(Err)
                        Err = tringing(blk,dut,drx,dtx)
                        Errs.append(Err)

                    except KeyError:
                        veprints(2,'?')
                    except ValueError:
                        veprints(2,'!')
                    except TimeoutError:
                        veprints(2,'T')
                    except RuntimeError:
                        veprints(2,'R')
                    except ZeroDivisionError:
                        veprints(2,'0')
                    else:
                        veprints(2,'.')
        
        veprint(2)
        
        if len(Errs) < 10:
            raise RuntimeError('calibrate_antd: Not enough measurements')

        Ecnt = len(Errs)
        Eavg = np.mean(Errs)
        Estd = np.std(Errs)

        if cfg.verbose > 2:
            print(f'STATISTICS [{loop}]              ')
            print(f'    Samples:   {Ecnt}')
            print(f'    Error:     {Eavg:.3f}m [{Estd:.3f}m]')
            print(f'    Corr:      {corr:+.1f}')
            print(f'    ANTD:      {current:#04x}')
        else:
            veprint(1, f' [{loop}] Error: {Eavg:.3f}m [{Estd:.3f}] {corr:+.1f}')
        
        error = Eavg / (Cabs / DW1000_CLOCK_HZ) / 2

        if -0.75 < error < 0.75:
            break
        
        corr += error
        
    return (current,corr)


def create_dw1000(rpc, name=None, host=None, port=None, coord=None, offset=None, rotation=None, role=None, group=None):

    if name is None:
        name = host.split('.')[0]
    if port is None:
        port = cfg.rpc_port
    if role is None:
        role = "DUT"
    if group is None:
        group = 0
    if coord is None:
        coord = [ 0.0, 0.0, 0.0 ]
    if offset is None:
        offset = [ 0.0, 0.0, 0.0 ]
    if rotation is None:
        rotation = [ 0.0, 0.0, 0.0 ]

    np_coord = np.array(coord)
    np_offset = np.array(offset)
    
    (a,b,c) = np.radians(rotation)

    A = np.array(((1.0, 0.0, 0.0), (0.0, cos(a), -sin(a)), (0.0, sin(a), cos(a))))
    B = np.array(((cos(b), 0.0, sin(b)), (0.0, 1.0, 0.0), (-sin(b), 0.0, cos(b))))
    C = np.array(((cos(c), -sin(c), 0.0), (sin(c), cos(c), 0.0), (0.0, 0.0, 1.0)))
    
    np_offset = dot(C,dot(B,dot(A,np_offset)))
    np_location = np_coord + np_offset

    veprint(4, f'{name} Coord:{np_coord} Offset:{np_offset} Location:{np_location}')

    adev = DW1000(rpc, name, host, port, np_location)
    
    setattr(adev, 'role', role)
    setattr(adev, 'group', group)

    veprint(1, f'Connecting to {adev.host}...')

    adev.connect()
    
    adev.set_dw1000_attr('channel', cfg.dw1000_channel)
    adev.set_dw1000_attr('prf', cfg.dw1000_prf)
    adev.set_dw1000_attr('pcode', cfg.dw1000_pcode)
    adev.set_dw1000_attr('rate', cfg.dw1000_rate)
    adev.set_dw1000_attr('txpsr', cfg.dw1000_txpsr)
    adev.set_dw1000_attr('smart_power', cfg.dw1000_smart)
    adev.set_dw1000_attr('tx_power', cfg.dw1000_power)
    
    return adev


def main():

    parser = argparse.ArgumentParser(description="DW1000 calibraturd")

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-D', '--debug', action='count', default=0)
    
    parser.add_argument('-c', '--config', type=str, default=cfg.config_json)

    parser.add_argument('-p', '--port', type=int)
    parser.add_argument('-n', '--count', type=int)
    parser.add_argument('-d', '--delay', type=float)
    parser.add_argument('-w', '--wait', type=float)
    parser.add_argument('-i', '--interval', type=float)
    parser.add_argument('-P', '--power', type=float)
    parser.add_argument('-C', '--coarse', type=int)
    parser.add_argument('-L', '--distance', type=float)
    parser.add_argument('-O', '--ppm-offset', type=float)
    
    parser.add_argument('--channel', type=int)
    parser.add_argument('--prf', type=int)
    parser.add_argument('--pcode', type=int)
    parser.add_argument('--rate', type=int)
    parser.add_argument('--txpsr', type=int)
    parser.add_argument('--txpwr', type=int)
    
    parser.add_argument('-X', '--calib-xtalt', action='store_true', default=False)
    parser.add_argument('-T', '--calib-txpower', action='store_true', default=False)
    parser.add_argument('-A', '--calib-antd', action='store_true', default=False)
    
    args = parser.parse_args()

    cfg.debug = args.debug
    cfg.verbose = args.verbose
    WPANFrame.verbosity = cfg.verbose

    cfg.config_json = args.config

    with open(cfg.config_json, 'r') as f:
        cfg.config = json.load(f)

    for (key,value) in cfg.config.get('DW1000').items():
        try:
            getattr(cfg,'dw1000_' + key)
            setattr(cfg,'dw1000_' + key,value)
        except AttributeError:
            eprint('Invalid DW1000 config {}: {}'.format(key,value))

    for (key,value) in cfg.config.get('CALIBRATOR').items():
        try:
            getattr(cfg,key)
            setattr(cfg,key,value)
        except AttributeError:
            eprint('Invalid CALIBRATOR config {}: {}'.format(key,value))

    cfg.setarg('rpc_port', args.port)

    cfg.setarg('blink_count', args.count)
    cfg.setarg('blink_delay', args.delay)
    cfg.setarg('blink_wait', args.wait)
    cfg.setarg('blink_interval', args.interval)
    
    cfg.setarg('txlevel', args.power)
    cfg.setarg('distance', args.distance)
    cfg.setarg('ppm_offset', args.ppm_offset)

    cfg.setarg('dw1000_channel', args.channel)
    cfg.setarg('dw1000_prf', args.prf)
    cfg.setarg('dw1000_pcode', args.pcode)
    cfg.setarg('dw1000_rate', args.rate)
    cfg.setarg('dw1000_txpsr', args.txpsr)
    cfg.setarg('dw1000_power', args.txpwr)
    
    cfg.setarg('rxlevel', RFCalcRxPower(cfg.dw1000_channel, cfg.distance, cfg.txlevel))
    

    ##
    ## Devices
    ##
    
    rpc = RPC()
    
    devs = [ ]
    duts = [ ]
    refs = [ ]
    grps = { 0:[], 1:[], 2:[] }

    for arg in cfg.config.get('ANCHORS'):
        try:
            host = arg['host']
            adev = create_dw1000(rpc, **arg)
            devs.append(adev)
            if adev.role == 'DUT':
                duts.append(adev)
            elif adev.role == 'REF':
                refs.append(adev)
                grps[adev.group].append(adev)

        except (OSError,ConnectionError) as err:
            raise RuntimeError(f'Remote host {host} not available: {err}')

    if args.verbose > 1:
        DW1000.print_all_remote_attrs(devs,True)


    ##
    ## Calibration
    ##

    blk = Blinks(rpc)

    rxpwr = cfg.rxlevel
    txpwr = DW1000.tx_power_reg_to_list( duts[0].get_dw1000_attr('tx_power') )

    if args.coarse is not None:
        txpwr[0] = args.coarse

    try:
        if args.calib_xtalt:
            for dut in duts:
                xtalt = calibrate_xtalt(blk,dut,refs)
                print('XTALT,{:s},{:d}'.format(dut.name,xtalt))
        
        if args.calib_txpower:
            for dut in duts:
                txpwr = calibrate_txpower(blk,dut,refs,txpwr,rxpwr)
                print('TXPWR,{0:s},0x{1:02x},{2[0]:},{2[1]:}'.format(dut.name,DW1000.tx_power_list_to_code(txpwr),txpwr))
        
        if args.calib_antd:
            for dut in duts:
                (antd,corr) = calibrate_antd(blk,dut,grps)
                print('ANTD,{:s},{:#04x}'.format(dut.name,antd))
    
    except KeyboardInterrupt:
        eprint('\rStopping...')
    except RuntimeError as err:
        errhandler('Runtime error', err)

    blk.stop()
    rpc.stop()


if __name__ == "__main__": main() 

