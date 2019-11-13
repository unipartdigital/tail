#!/usr/bin/python3
#
# Ranging tool for Tail algorithm development
#

import sys
import time
import math
import queue
import socket
import json
import argparse
import threading
import traceback

import numpy as np
import numpy.linalg as lin
import matplotlib.pyplot as plot

from tail import *
from dwarf import *
from blinks import *


class cfg():

    verbose = 0
    debug = 0
    
    rpc_port = 8912
    
    blink_count    = 100
    blink_delay    = 0.100
    blink_wait     = 0.500
    blink_interval = 1.000

    window         = 1.000
    binsize        = 2 / DW1000_CLOCK_GHZ


class data():
    
    Tcnt = 0

    delays = []
    powers = []
    fpaths = []
    power2 = []
    fpath2 = []
    rtrips = []
    xtppms = []
    temps1 = []
    temps2 = []
    temps3 = []


def TWR(blk, remotes, timing):

    dut1 = remotes[0]
    dut2 = remotes[1]

    i1 = blk.blink(dut1)
    blk.nap(timing[0])
    i2 = blk.blink(dut2)
    blk.nap(timing[1])
    i3 = blk.blink(dut1)
    
    blk.wait_blinks((i1,i2,i3),remotes,timing[2])

    T = [ None, None, None, None, None, None ]
    
    T[0] = blk.get_rawts(i1, dut1)
    T[1] = blk.get_rawts(i1, dut2)
    T[2] = blk.get_rawts(i2, dut2)
    T[3] = blk.get_rawts(i2, dut1)
    T[4] = blk.get_rawts(i3, dut1)
    T[5] = blk.get_rawts(i3, dut2)
    
    T41 = T[3] - T[0]
    T32 = T[2] - T[1]
    T54 = T[4] - T[3]
    T63 = T[5] - T[2]
    T51 = T[4] - T[0]
    T62 = T[5] - T[1]
    
    Tof = (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / DW1000_CLOCK_HZ
    Lof = Dof * Cabs
    
    if Lof < -1.0 or Lof > 100.0:
        raise ValueError(f'Ranging: LoF out of bounds: {Lof} T:{T}')

    Rtt = T41 / DW1000_CLOCK_HZ
    
    F2 = blk.get_xtal_ratio(i1, dut2)
    F4 = blk.get_xtal_ratio(i2, dut1)

    Pwr = blk.get_rx_level(i2, dut1)
    Fpp = blk.get_fp_level(i2, dut1)
    
    Tmp1 = blk.get_temp(i1,dut1)
    Tmp2 = blk.get_temp(i2,dut2)

    Est = (F2 + F4) / 2
    Err = (T62 - T51) / T62
    
    blk.purge_blink(i1)
    blk.purge_blink(i2)
    blk.purge_blink(i3)
    
    return (Lof,Dof,Rtt,Err,Est,Pwr,Fpp,Tmp1,Tmp2)


def do_ranging(blk, remotes, timing):

    for i in range(cfg.blink_count):
    
        try:
            (Lof,Dof,Rtt,Err,Est,Pwr,Fpp,T1,T2) = TWR(blk, remotes, timing)

            data.delays.append(Dof)
            data.powers.append(Pwr)
            data.fpaths.append(Fpp)
            data.xtppms.append(Err)
            data.rtrips.append(Rtt)
            data.temps1.append(T1)
            data.temps2.append(T2)

            data.Tcnt += 1

            if cfg.verbose > 0:
                Plog = RxPower2dBm(Pwr,cfg.prf)
                msg  = ' ** '
                msg += 'Lof:{:.3f}m '.format(Lof)
                msg += 'DoF:{:.3f}ns '.format(Dof*1E9)
                msg += 'Xerr:{:+.3f}ppm '.format(Err*1E6)
                msg += 'Xest:{:+.3f}ppm '.format(Est*1E6)
                msg += 'Pwr:{:.1f}dBm '.format(Plog)
                msg += 'T1:{:.2f}°C '.format(T1)
                msg += 'T2:{:.2f}°C '.format(T2)
                msg += 'RTT:{:.3f}ms '.format(Rtt*1E3)
                print(msg)

        except Exception as err:
            errhandler('FAIL', err)

        try:
            pass
        except (TimeoutError):
            eprints('T')
        except (TypeError):
            eprints('x')
        except (KeyError):
            eprints('?')
        except (ValueError):
            eprints('*')
        except (ZeroDivisionError):
            eprints('0')

        if cfg.verbose == 0 and i%10 == 0:
            eprints('.')

        blk.nap(cfg.blink_interval)


def T3WR(blk, remotes, timing):

    dut = remotes[0]
    dtx = remotes[1]
    drx = remotes[2]

    i1 = blk.blink(dtx)
    blk.nap(timing[0])
    i2 = blk.blink(dut)
    blk.nap(timing[1])
    i3 = blk.blink(dtx)
    
    blk.wait_blinks((i1,i2,i3),remotes,timing[2])

    T = [ None, None, None, None, None, None ]
    
    T[0] = blk.get_rawts(i1, drx)
    T[1] = blk.get_rawts(i1, dut)
    T[2] = blk.get_rawts(i2, dut)
    T[3] = blk.get_rawts(i2, drx)
    T[4] = blk.get_rawts(i3, drx)
    T[5] = blk.get_rawts(i3, dut)
    
    T41 = T[3] - T[0]
    T32 = T[2] - T[1]
    T54 = T[4] - T[3]
    T63 = T[5] - T[2]
    T51 = T[4] - T[0]
    T62 = T[5] - T[1]
    
    Tof = 2 * (T41*T63 - T32*T54) / (T51+T62)
    Dof = Tof / DW1000_CLOCK_HZ
    Lof = Dof * Cabs
    
    if Lof < -100.0 or Lof > 100.0:
        raise ValueError(f'Ranging: LoF out of bounds: {Lof} T:{T}')

    Rtt = T41 / DW1000_CLOCK_HZ
    
    Est = blk.get_xtal_ratio(i2, drx)
    Err = (T51 - T62) / T51
    
    Pw1 = blk.get_rx_level(i2, drx)
    Fp1 = blk.get_fp_level(i2, drx)
    Pw2 = blk.get_rx_level(i1, drx)
    Fp2 = blk.get_fp_level(i1, drx)

    Tmp1 = blk.get_temp(i1,dut)
    Tmp2 = blk.get_temp(i1,dtx)
    Tmp3 = blk.get_temp(i1,drx)

    blk.purge_blink(i1)
    blk.purge_blink(i2)
    blk.purge_blink(i3)
    
    return (Lof,Dof,Rtt,Err,Est,Pw1,Fp1,Pw2,Fp2,Tmp1,Tmp2,Tmp3)


def do_tringing(blk, remotes, timing):
    
    for i in range(cfg.blink_count):
        
        try:
            (Lof,Dof,Rtt,Err,Est,Pw1,Fp1,Pw2,Fp2,T1,T2,T3) = T3WR(blk, remotes, timing)

            data.delays.append(Dof)
            data.powers.append(Pw1)
            data.fpaths.append(Fp1)
            data.power2.append(Pw2)
            data.fpath2.append(Fp2)
            data.xtppms.append(Err)
            data.rtrips.append(Rtt)
            data.temps1.append(T1)
            data.temps2.append(T2)
            data.temps3.append(T3)

            data.Tcnt += 1

            if cfg.verbose > 0:
                P1 = RxPower2dBm(Pw1,cfg.prf)
                P2 = RxPower2dBm(Pw2,cfg.prf)
                msg  = ' ** '
                msg += 'Lof:{:.3f}m '.format(Lof)
                msg += 'DoF:{:.3f}ns '.format(Dof*1E9)
                msg += 'Xerr:{:+.3f}ppm '.format(Err*1E6)
                msg += 'Xest:{:+.3f}ppm '.format(Est*1E6)
                msg += 'Pwr1:{:.1f}dBm '.format(P1)
                msg += 'Pwr2:{:.1f}dBm '.format(P2)
                msg += 'T1:{:.2f}°C '.format(T1)
                msg += 'T2:{:.2f}°C '.format(T2)
                msg += 'T3:{:.2f}°C '.format(T3)
                msg += 'RTT:{:.3f}ms '.format(Rtt*1E3)
                print(msg)

        except Exception as err:
            errhandler('FAIL', err)

        try:
            pass
        except (TimeoutError):
            eprints('T')
        except (TypeError):
            eprints('x')
        except (KeyError):
            eprints('?')
        except (ValueError):
            eprints('*')
        except (ZeroDivisionError):
            eprints('0')

        if cfg.verbose == 0 and i%10 == 0:
            eprints('.')

        blk.nap(cfg.blink_interval)

            
def plot_data():

    if data.Tcnt > 3:
        
        Davg = np.mean(data.delays)
        Dstd = np.std(data.delays)
        Dmed = np.median(data.delays)
        
        Lavg = Davg * Cabs
        Lstd = Dstd * Cabs
        Lmed = Dmed * Cabs
        
        (Navg,Nstd) = fpeak(data.delays)
        
        Mavg = Navg * Cabs
        Mstd = Nstd * Cabs

        if len(data.temps1) > 0:
            T1avg = np.mean(data.temps1)
        else:
            T1avg = None

        if len(data.temps2) > 0:
            T2avg = np.mean(data.temps2)
        else:
            T2avg = None
        
        if len(data.temps3) > 0:
            T3avg = np.mean(data.temps3)
        else:
            T3avg = None
            
        if len(data.xtppms) > 0:
            Xavg  = np.mean(data.xtppms)
            Xstd  = np.std(data.xtppms)
        else:
            Xavg  = None
            
        if len(data.powers) > 0:
            Pavg = np.mean(data.powers)
            Pstd = np.std(data.powers)
            Favg = np.mean(data.fpaths)
            Fstd = np.std(data.fpaths)
            Plog = RxPower2dBm(Pavg,cfg.prf)
            Pstl = RxPower2dBm(Pavg+Pstd,cfg.prf) - Plog
            Flog = RxPower2dBm(Favg,cfg.prf)
            Fstl = RxPower2dBm(Favg+Fstd,cfg.prf) - Flog
        else:
            Pavg = None

        if len(data.power2) > 0:
            P2avg = np.mean(data.power2)
            P2std = np.std(data.power2)
            F2avg = np.mean(data.fpath2)
            F2std = np.std(data.fpath2)
            P2log = RxPower2dBm(P2avg,cfg.prf)
            P2stl = RxPower2dBm(P2avg+P2std,cfg.prf) - P2log
            F2log = RxPower2dBm(F2avg,cfg.prf)
            F2stl = RxPower2dBm(F2avg+F2std,cfg.prf) - F2log
        else:
            P2avg = None
            
        print()
        print('FINAL STATISTICS:')
        print('  Samples:    {}/{} [{:.1f}%]'.format(data.Tcnt,cfg.blink_count, (100*data.Tcnt/cfg.blink_count)-100))
        print('  Dist:       {:.3f}m [{:.3f}m]'.format(Lavg,Lstd))
        print('  Peak:       {:.3f}m [{:.3f}m]'.format(Mavg,Mstd))
        
        if Pavg:
            print('  Power:      {:+.1f}dBm [{:.2f}dB]'.format(Plog,Pstl))
            print('  FPath:      {:+.1f}dBm [{:.2f}dB]'.format(Flog,Fstl))
        if P2avg:
            print('  Power2:     {:+.1f}dBm [{:.2f}dB]'.format(P2log,P2stl))
            print('  FPath2:     {:+.1f}dBm [{:.2f}dB]'.format(F2log,F2stl))
        if Xavg:
            print('  XtalPPM:    {:+.2f}ppm [{:.2f}ppm]'.format(Xavg*1E6,Xstd*1E6))
        if T1avg:
            print('  Temp1:      {:.1f}°C'.format(T1avg))
        if T2avg:
            print('  Temp2:      {:.1f}°C'.format(T2avg))
        if T3avg:
            print('  Temp3:      {:.1f}°C'.format(T3avg))

        if cfg.histogram or cfg.plot:
            
            Hbin = cfg.binsize
            if cfg.window > 0:
                Hrng = cfg.window
            else:
                Hrng = -2.0 * cfg.window * Dstd

            Hmin = Davg - Hrng/2
            Hmax = Davg + Hrng/2
            Hcnt = int(Hrng/Hbin) + 1
            bins = frange(Hmin,Hmax,Hcnt)
        
            (hist,edges) = np.histogram(data.delays,bins=bins)

            if cfg.histogram:
                print()
                print('HISTOGRAM:')
                for i in range(len(hist)):
                    print('   {:.3f}: {:d}'.format(edges[i],hist[i]))

            if cfg.plot:
                fig,ax = plot.subplots(figsize=(15,10),dpi=80)
                ax.set_title('Delay distribution {}'.format(time.strftime('%d/%m/%Y %H:%M:%S')))
                ax.set_xlabel('Delay [ns]')
                ax.set_ylabel('Samples')
                ax.text(0.80, 0.95, r'P={:.3f}m'.format(Mavg), transform=ax.transAxes, size='x-large')
                ax.text(0.80, 0.90, r'p={:.3f}m'.format(Mstd), transform=ax.transAxes, size='x-large')
                ax.text(0.80, 0.85, r'$\mu$={:.3f}m'.format(Lavg), transform=ax.transAxes, size='x-large')
                ax.text(0.80, 0.80, r'$\sigma$={:.3f}m'.format(Lstd), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.95, r'P={:.3f}ns'.format(Navg), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.90, r'p={:.3f}ns'.format(Nstd), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.85, r'$\mu$={:.3f}ns'.format(Davg), transform=ax.transAxes, size='x-large')
                ax.text(0.90, 0.80, r'$\sigma$={:.3f}ns'.format(Dstd), transform=ax.transAxes, size='x-large')
                ax.grid(True)
                ax.hist(data.delays,bins)
                fig.tight_layout()
                plot.show()
        
    print()



def main():
    
    parser = argparse.ArgumentParser(description="TWR ranging tool")

    DW1000.add_device_arguments(parser)
    
    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count, help='Number of blinks')
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay, help='Delay between blinks')
    parser.add_argument('-w', '--wait', type=float, default=cfg.blink_wait, help='Time to wait timestamp reception')
    parser.add_argument('-i', '--interval', type=float, default=cfg.blink_interval, help='Time between rangings')
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port, help='RPC port')
    parser.add_argument('-H', '--hist', action='store_true', default=False, help='Print histogram')
    parser.add_argument('-P', '--plot', action='store_true', default=False, help='Plot histogram')
    parser.add_argument('-T', '--tringing', action='store_true', default=False, help='Three-Way Ranging')
    parser.add_argument('--window', type=float, default=cfg.window)
    parser.add_argument('--binsize', type=float, default=cfg.binsize)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    WPANFrame.verbosity = args.verbose
    cfg.verbose = args.verbose
    cfg.debug = args.debug

    cfg.tringing = args.tringing

    cfg.blink_count = args.count
    cfg.blink_delay = args.delay
    cfg.blink_wait  = args.wait
    cfg.blink_interval = args.interval
    
    cfg.rpc_port = args.port

    cfg.histogram = args.hist
    cfg.plot = args.plot

    cfg.window = args.window
    cfg.binsize = args.binsize
    
    rpc = RPC()

    remotes = []
    for host in args.remote:
        name = host.split('.')[0]
        try:
            anchor = DW1000(rpc,name,host,cfg.rpc_port)
            anchor.connect()
            remotes.append(anchor)
        except (ValueError,ConnectionError):
            eprint(f'Remote {host} not accessible')

    DW1000.handle_device_arguments(args,remotes)
    
    if cfg.verbose > 0:
        DW1000.print_all_remote_attrs(remotes, True)

    timing = (args.delay, args.delay, args.wait)
        
    cfg.ch  = int(remotes[0].get_dw1000_attr('channel'))
    cfg.prf = int(remotes[0].get_dw1000_attr('prf'))

    blk = Blinks(rpc)

    try:
        if cfg.tringing:
            do_tringing(blk,remotes,timing)
        else:
            do_ranging(blk,remotes,timing)
    
    except KeyboardInterrupt:
        eprint('\nStopping...')

    plot_data()

    blk.stop()
    rpc.stop()
    

if __name__ == "__main__": main()

