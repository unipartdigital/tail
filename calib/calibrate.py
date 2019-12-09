#!/usr/bin/python3
#
# Automatic DW1000 calibration
#

import sys
import math
import argparse

import numpy as np
import subprocess as sub

from tail import *
from dwarf import *
from blinks import *

from numpy import dot, sin, cos


class cfg():

    debug           = 0
    verbose         = 0

    setup_json      = "setup.json"
    calib_json      = "calib.json"

    program         = False

    calib_antd      = False
    calib_xtalt     = False
    calib_txpower   = False
    
    dw1000_profile  = None
    dw1000_channel  = 5
    dw1000_pcode    = 12
    dw1000_prf      = 64
    dw1000_rate     = 850
    dw1000_txpsr    = 1024
    dw1000_smart    = 0
    dw1000_power    = '0x88888888'
    dw1000_txlevel  = -12.3

    blink_count     = 100
    blink_delay     = 0.050
    blink_wait      = 0.500
    blink_interval  = 0.250

    ppm_offset      = 0.0
    rpc_port        = 9812

    anchors         = []

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
            
    if len(Errs) < cfg.blink_count:
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

        if -100 < Eavg < 100 and Estd < 3:
            if Eavg < 0.0:
                TL = xtalt
            else:
                TH = xtalt

    veprint(1, 'Calibrating {} <{}> XTALT {}'.format(dut.name,dut.eui,best))

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
                        Dist = dut.distance_to(dev)
                        Pest = RFCalcRxPower(cfg.dw1000_channel, Dist, cfg.dw1000_txlevel)
                        
                        Plog = RxPower2dBm(Plin,cfg.dw1000_prf) - Pest
                        Flog = RxPower2dBm(Flin,cfg.dw1000_prf) - Pest
                        
                        Power.append(Plog)
                        Fpath.append(Flog)
                    
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
    Favg = np.mean(Fpath)
    Fstd = np.std(Fpath)
    Tavg = np.mean(Temps)
    Tstd = np.std(Temps)
    Vavg = np.mean(Volts)
    Vstd = np.std(Volts)
    
    Tcnt = len(Temps)
    Rate = Tcnt / cfg.blink_count
    
    return (Tcnt,Rate,Pavg,Pstd,Favg,Fstd,Tavg,Tstd,Vavg,Vstd)


def calibrate_txpower(blk, dut, refs):

    txpwr = DW1000.tx_power_reg_to_list(dut.get_dw1000_attr('tx_power'))

    veprint(1, 'Calibrating {} <{}> Initial TxPWR:{} TxLevel:{:.1f}dBm'.format(dut.name,dut.eui,txpwr,cfg.dw1000_txlevel))

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

        (Tcnt,Rate,Pavg,Pstd,Favg,Fstd,Tavg,Tstd,Vavg,Vstd) = estimate_txpower(blk, dut, refs)

        fail = 100 * (1.0 - Rate)

        if cfg.verbose > 2:
            eprint(f'STATISTICS [{loop}] [{TL}:{TX}:{TH}]')
            eprint(f'    Samples:   {Tcnt} [{fail:.1f}%]')
            eprint(f'    Temp:      {Tavg:.1f}°C [{Tstd:.2f}°C]')
            eprint(f'    Volt:      {Vavg:.3f}V [{Vstd:.3f}V]')
            eprint(f'    TxPWR:     [{txpwr[0]:.0f}{txpwr[1]:+.1f}]')
            eprint(f'    RxPWR:     {Pavg:+.1f}dBm [{Pstd:.2f}dBm]')
            eprint(f'    FpPWR:     {Favg:+.1f}dBm [{Fstd:.2f}dBm]')
        else:
            veprint(1, f' [{loop}] TxPwr: {txpwr[0]:.0f}{txpwr[1]:+.1f}dBm RxPWR:{Pavg:+.1f}dBm FpPWR:{Favg:+.1f}dBm')

        errors[TX] = Pavg

        if -20 < Pavg < 20 and Pstd < 10.0:
            if Pavg < 0.0:
                TL = TX
            else:
                TH = TX

    veprint(1, 'Calibrating {} <{}> DONE TxPWR:{} TxLevel:{:.1f}dBm'.format(dut.name,dut.eui,txpwr,cfg.dw1000_txlevel))

    dut.set_dw1000_attr('tx_power', DW1000.tx_power_list_to_code(txpwr))

    return DW1000.tx_power_list_to_code(txpwr)
    

def trcalc(blk, idx, dut, dtx, drx):

    T1 = blk.get_rawts(idx[0], drx)
    T2 = blk.get_rawts(idx[0], dut)
    T3 = blk.get_rawts(idx[1], dut)
    T4 = blk.get_rawts(idx[1], drx)
    T5 = blk.get_rawts(idx[2], drx)
    T6 = blk.get_rawts(idx[2], dut)
    
    T41 = T4 - T1
    T32 = T3 - T2
    T54 = T5 - T4
    T63 = T6 - T3
    T51 = T5 - T1
    T62 = T6 - T2
    
    Tof = 2* (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / DW1000_CLOCK_HZ
    Lof = Dof * Cabs

    D1 = dtx.distance_to(drx)
    D2 = dtx.distance_to(dut)
    D3 = dut.distance_to(drx)
    
    Loe = D3 + (D2 - D1)
    Err = Lof - Loe

    veprint(5, f'\rDUT:{dut.name} DTX:{dtx.name} DRX:{drx.name} DUTTX:{D1:.3f} DTXRX:{D2:.3f} DUTRX:{D3:.3f} Loe:{Loe:.3f} Lof:{Lof:.3f} Err:{Err:.3f}')

    if Err < -10 or Err > 10:
        raise ValueError(f'Tringing: Err out of bounds: {Err}')
    
    return Err


def calibrate_antd(blk, dut, grps):

    antd = 0x4040
    corr = 0.0
    
    veprint(1, 'Calibrating {} <{}> ANTD'.format(dut.name,dut.eui))

    for loop in range(10):

        current = int(round(antd+corr))
        
        dut.set_dw1000_attr('antd', current)
        
        Errs = [ ]

        count = cfg.blink_count // (len(grps[1]) + len(grps[2]))
        
        for i in range(count):
            
            for dtx in grps[1]:
                
                grp = [dut,dtx] + grps[2]

                blk.sync(cfg.blink_interval)
    
                i1 = blk.blink(dtx)
                blk.nap(cfg.blink_delay)
                i2 = blk.blink(dut)
                blk.nap(cfg.blink_delay)
                i3 = blk.blink(dtx)

                idx = (i1,i2,i3)

                blk.wait_blinks(idx,grp,cfg.blink_wait)
    
                for drx in grps[2]:
                    try:
                        Err = trcalc(blk,idx,dut,dtx,drx)
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

            for dtx in grps[2]:
                
                grp = [dut,dtx] + grps[1]

                blk.sync(cfg.blink_interval)
    
                i1 = blk.blink(dtx)
                blk.nap(cfg.blink_delay)
                i2 = blk.blink(dut)
                blk.nap(cfg.blink_delay)
                i3 = blk.blink(dtx)

                idx = (i1,i2,i3)

                blk.wait_blinks(idx,grp,cfg.blink_wait)
    
                for drx in grps[1]:
                    try:
                        Err = trcalc(blk,idx,dut,dtx,drx)
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
        
        if len(Errs) < cfg.blink_count:
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

        if -1 < error < 1:
            break
        
        corr += error

    veprint(1, 'Calibrating {} <{}> ANTD:{:#04x}'.format(dut.name,dut.eui,current))
    
    return current


def program_dw1000(dut):

    cmd = f'modhat'
    if dut.xtalt:
        cmd += f' -X {dut.xtalt}'
    if dut.txpwr:
        cmd += f' -T 0x{dut.txpwr:02x}{dut.txpwr:02x}{dut.txpwr:02x}{dut.txpwr:02x}'
    if dut.antd:
        cmd += f' -A {dut.antd:#04x}'
        # Fixme with profiles - PRF16 should be calibrated separately
        cmd += f' -a {dut.antd:#04x}'
    
    ssh = sub.run(['ssh', f'root@{dut.host}', cmd], timeout=30)

    return ssh.returncode


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

    setattr(adev, 'xtalt', None)
    setattr(adev, 'txpwr', None)
    setattr(adev, 'antd', None)

    veprint(2, f'Connecting to {adev.host}...')

    adev.connect()
    
    adev.set_dw1000_attr('channel', cfg.dw1000_channel)
    adev.set_dw1000_attr('prf', cfg.dw1000_prf)
    adev.set_dw1000_attr('pcode', cfg.dw1000_pcode)
    adev.set_dw1000_attr('rate', cfg.dw1000_rate)
    adev.set_dw1000_attr('txpsr', cfg.dw1000_txpsr)
    adev.set_dw1000_attr('smart_power', cfg.dw1000_smart)
    adev.set_dw1000_attr('tx_power', cfg.dw1000_power)
    
    return adev


def load_dict(input, output, prefix=''):
    for (key,value) in input.items():
        try:
            getattr(output, prefix + key)
            setattr(output, prefix + key, value)
        except AttributeError:
            eprint('Invalid setup {}: {}'.format(key,value))

def load_list(input, output, prefix=''):
    for value in input:
        output.append(value)


def main():

    parser = argparse.ArgumentParser(description="DW1000 calibraturd")

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-D', '--debug', action='count', default=0)
    
    parser.add_argument('-s', '--setup', type=str, default=cfg.setup_json)
    parser.add_argument('-c', '--calib', type=str, default=cfg.calib_json)

    parser.add_argument('-A', '--calib-antd', action='store_true', default=None)
    parser.add_argument('-X', '--calib-xtalt', action='store_true', default=None)
    parser.add_argument('-T', '--calib-txpower', action='store_true', default=None)
    parser.add_argument('-P', '--program', action='store_true', default=None)
    
    parser.add_argument('-p', '--port', type=int)
    parser.add_argument('-n', '--count', type=int)
    parser.add_argument('-d', '--delay', type=float)
    parser.add_argument('-w', '--wait', type=float)
    parser.add_argument('-i', '--interval', type=float)
    parser.add_argument('-O', '--ppm-offset', type=float)
    
    parser.add_argument('--channel', type=int)
    parser.add_argument('--prf', type=int)
    parser.add_argument('--pcode', type=int)
    parser.add_argument('--rate', type=int)
    parser.add_argument('--txpsr', type=int)
    parser.add_argument('--txpwr', type=int)
    parser.add_argument('--txlevel', type=float)

    args = parser.parse_args()

    cfg.debug = args.debug
    cfg.verbose = args.verbose
    WPANFrame.verbosity = cfg.verbose

    cfg.calib_json = args.calib
    cfg.setup_json = args.setup

    with open(cfg.calib_json, 'r') as f:
        calib = json.load(f)

    with open(cfg.setup_json, 'r') as f:
        setup = json.load(f)

    load_list(setup.get('ANCHORS'), cfg.anchors)
    load_dict(calib.get('DW1000'), cfg, 'dw1000_')
    load_dict(calib.get('CALIBRATE'), cfg)

    cfg.setarg('program', args.program)
    cfg.setarg('calib_antd', args.calib_antd)
    cfg.setarg('calib_xtalt', args.calib_xtalt)
    cfg.setarg('calib_txpower', args.calib_txpower)
    
    cfg.setarg('dw1000_channel', args.channel)
    cfg.setarg('dw1000_prf', args.prf)
    cfg.setarg('dw1000_pcode', args.pcode)
    cfg.setarg('dw1000_rate', args.rate)
    cfg.setarg('dw1000_txpsr', args.txpsr)
    cfg.setarg('dw1000_power', args.txpwr)
    cfg.setarg('dw1000_txlevel', args.txlevel)
    
    cfg.setarg('blink_count', args.count)
    cfg.setarg('blink_delay', args.delay)
    cfg.setarg('blink_wait', args.wait)
    cfg.setarg('blink_interval', args.interval)
    
    cfg.setarg('rpc_port', args.port)
    cfg.setarg('ppm_offset', args.ppm_offset)


    ##
    ## Devices
    ##
    
    rpc = RPC()
    
    devs = [ ]
    duts = [ ]
    refs = [ ]
    grps = { 0:[], 1:[], 2:[] }

    for arg in cfg.anchors:
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

    try:
        for dut in duts:

            if cfg.calib_xtalt:
                dut.xtalt = calibrate_xtalt(blk,dut,refs)
            if cfg.calib_txpower:
                dut.txpwr = calibrate_txpower(blk,dut,refs)
            if cfg.calib_antd:
                dut.antd = calibrate_antd(blk,dut,grps)

            prints(f'{dut.name} <{dut.eui}>')
            
            if dut.xtalt:
                prints(f' XTALT:{dut.xtalt}')
            if dut.txpwr:
                prints(f' TXPWR:0x{dut.txpwr:02x}')
            if dut.antd:
                prints(f' ANTD:0x{dut.antd:04x}')

            prints('\n')

            if cfg.program:
                eprint(f'Programming {dut.name}')
                program_dw1000(dut)

    except KeyboardInterrupt:
        eprint('\rStopping...')
    except RuntimeError as err:
        errhandler('Runtime error', err)

    blk.stop()
    rpc.stop()


if __name__ == "__main__": main() 

