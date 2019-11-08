#!/usr/bin/python3
#
# Anchor distance tool for Tail algorithm development
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

    debug = 0

    rpc_port     = 8912
    
    blink_count  = 100
    blink_delay  = 0.050
    blink_wait   = 1.000

    window       = 1.000
    binsize      = 2 / DW1000_CLOCK_GHZ




    
def TWR(blk, remotes, timing):

    rem1 = remotes[0]
    rem2 = remotes[1]

    blk.sync()
    i1 = blk.blink(rem1)
    blk.nap(timing[0])
    i2 = blk.blink(rem2)
    blk.nap(timing[1])
    i3 = blk.blink(rem1)
    
    blk.wait_blinks((i1,i2,i3),remotes,timing[2])

    T = [ None, None, None, None, None, None ]
    
    T[0] = blk.get_rawts(i1, rem1)
    T[1] = blk.get_rawts(i1, rem2)
    T[2] = blk.get_rawts(i2, rem2)
    T[3] = blk.get_rawts(i2, rem1)
    T[4] = blk.get_rawts(i3, rem1)
    T[5] = blk.get_rawts(i3, rem2)
    
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
    
    #F2 = blk.get_xtal_ratio(i1, rem2)
    #F4 = blk.get_xtal_ratio(i2, rem1)

    Pwr = blk.get_rx_level(i2, rem1)
    Fpp = blk.get_fp_level(i2, rem1)
    
    Tmp1 = blk.get_temp(i1,rem1)
    Tmp2 = blk.get_temp(i2,rem2)

    #Est = (F2 - F4) / 2
    Err = (T62 - T51) / T62
    
    blk.purge_blink(i1)
    blk.purge_blink(i2)
    blk.purge_blink(i3)
    
    return (Lof,Dof,Rtt,Err,Err,Pwr,Fpp,Tmp1,Tmp2)


            
def main():
    
    parser = argparse.ArgumentParser(description="TWR ranging tool")

    DW1000.add_device_arguments(parser)
    
    parser.add_argument('-D', '--debug', action='count', default=0, help='Enable debug prints')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity')
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count, help='Number of blinks')
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay, help='Delay between blinks')
    parser.add_argument('-w', '--wait', type=float, default=cfg.blink_wait, help='Time to wait timestamp reception')
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port, help='RPC port')
    parser.add_argument('-H', '--hist', action='store_true', default=False, help='Print histogram')
    parser.add_argument('-P', '--plot', action='store_true', default=False, help='Plot histogram')
    parser.add_argument('-R', '--raw', action='store_true', default=False, help='Use raw timestamps')
    parser.add_argument('-C', '--comp', action='store_true', default=False, help='Use Rx-comp')
    parser.add_argument('--delay1', type=float, default=None)
    parser.add_argument('--delay2', type=float, default=None)
    parser.add_argument('--window', type=float, default=cfg.window)
    parser.add_argument('--binsize', type=float, default=cfg.binsize)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    WPANFrame.verbosity = args.verbose
    cfg.debug = args.debug

    rpc = RPC()

    remotes = []
    for host in args.remote:
        name = host.split('.')[0]
        try:
            anchor = DW1000(rpc,name,host,args.port)
            anchor.connect()
            remotes.append(anchor)
        except (ValueError,ConnectionError):
            eprint(f'Remote {host} not accessible')

    DW1000.handle_device_arguments(args,remotes)
    
    if args.verbose > 0:
        DW1000.print_all_remote_attrs(remotes)

    ch  = int(remotes[0].get_dw1000_attr('channel'))
    prf = int(remotes[0].get_dw1000_attr('prf'))
    
    delay1 = args.delay
    delay2 = args.delay
    delay3 = args.wait
    
    if args.delay1:
        delay1 = args.delay1
    if args.delay2:
        delay2 = args.delay2

    timing = (delay1,delay2,delay3)

    blk = Blinks(rpc)

    Tcnt = 0

    delays = []
    powers = []
    fpaths = []
    rtrips = []
    xtppms = []
    temps1 = []
    temps2 = []

    try:
        for i in range(args.count):
            try:
                (Lof,Dof,Rtt,Ppm,Ppe,Pwr,Fpp,T1,T2) = TWR(blk, remotes, timing)
                
                delays.append(Dof)
                powers.append(Pwr)
                fpaths.append(Fpp)
                xtppms.append(Ppm*1E6)
                rtrips.append(Rtt)
                temps1.append(T1)
                temps2.append(T2)
                
                Tcnt += 1
                
                if args.verbose > 0:
                    Plog = RxPower2dBm(Pwr,prf)
                    msg  = ' ** '
                    msg += 'Lof:{:.3f}m '.format(Lof)
                    msg += 'DoF:{:.3f}ns '.format(Dof*1E9)
                    msg += 'Xerr:{:+.3f}ppm '.format(Ppm*1E6)
                    msg += 'Xest:{:+.3f}ppm '.format(Ppe*1E6)
                    msg += 'Pwr:{:.1f}dBm '.format(Plog)
                    msg += 'Temp1:{:.2f}°C '.format(T1)
                    msg += 'Temp2:{:.2f}°C '.format(T2)
                    msg += 'Rtt:{:.3f}ms '.format(Rtt*1E3)
                    print(msg)

            except Exception as err:
                errhandler('Ranging failure', err)

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

            if args.verbose == 0 and i%10 == 0:
                eprints('.')
            
    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    if Tcnt > 0:
        Davg = np.mean(delays)
        Dstd = np.std(delays)
        Dmed = np.median(delays)
        
        Lavg = Davg * Cabs
        Lstd = Dstd * Cabs
        Lmed = Dmed * Cabs
        
        (Navg,Nstd) = fpeak(delays)
        
        Mavg = Navg * Cabs
        Mstd = Nstd * Cabs
        
        Xavg  = np.mean(xtppms)
        Xstd  = np.std(xtppms)
        T1avg = np.mean(temps1)
        T2avg = np.mean(temps2)
        
        Pavg = np.mean(powers)
        Pstd = np.std(powers)
        Favg = np.mean(fpaths)
        Fstd = np.std(fpaths)
        
        Plog = RxPower2dBm(Pavg,prf)
        Pstl = RxPower2dBm(Pavg+Pstd,prf) - Plog
        Flog = RxPower2dBm(Favg,prf)
        Fstl = RxPower2dBm(Favg+Fstd,prf) - Flog

        print()
        print('FINAL STATISTICS:')
        print('  Samples:    {} [{:.1f}%]'.format(Tcnt,(100*Tcnt/args.count)-100))
        print('  Dist:       {:.3f}m [{:.3f}m]'.format(Lavg,Lstd))
        print('  Peak:       {:.3f}m [{:.3f}m]'.format(Mavg,Mstd))
        print('  Power:      {:+.1f}dBm [{:.2f}dB]'.format(Plog,Pstl))
        print('  FPath:      {:+.1f}dBm [{:.2f}dB]'.format(Flog,Fstl))
        print('  Xtal:       {:+.2f}ppm [{:.2f}ppm]'.format(Xavg,Xstd))
        print('  Temps:      {:.1f}°C {:.1f}°C'.format(T1avg,T2avg))

        if args.hist or args.plot:
            
            Hbin = args.binsize
            if args.window > 0:
                Hrng = args.window
            else:
                Hrng = -2.0 * args.window * Dstd

            Hmin = Davg - Hrng/2
            Hmax = Davg + Hrng/2
            Hcnt = int(Hrng/Hbin) + 1
            bins = frange(Hmin,Hmax,Hcnt)
        
            (hist,edges) = np.histogram(delays,bins=bins)

            if args.hist:
                print()
                print('HISTOGRAM:')
                for i in range(len(hist)):
                    print('   {:.3f}: {:d}'.format(edges[i],hist[i]))

            if args.plot:
                fig,ax = plot.subplots(figsize=(15,10),dpi=80)
                ax.set_title('Delay distribution {} - {} @ {}'.format(remotes[0].host,remotes[1].host,
                                                                      time.strftime('%d/%m/%Y %H:%M:%S')))
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
                ax.hist(delays,bins)
                fig.tight_layout()
                plot.show()
        
    else:
        print()
        print('NO SUITABLE SAMPLES')


if __name__ == "__main__":
    main()

