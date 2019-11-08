#!/usr/bin/python3
#
# DW1000 XTAL speed check against NTP
#
# Usage:  xtaltrim.py xmit* recv1 recv2 recv3 ... [usual args]
#
# Output:
#	Erx	Rx HWtime vs. Rx NTP synced clock over test period
#	Etx	Tx HWtime vs. Rx NTP synced clock over test period
#	Ediff	Erx-Etx
#	Eblks	Rx/Tx ratio from blinks (instantaneous)
#	Ettck	Rx/Tx ratio from DW1000 (ttcko/ttcki)
#	Pwr	Rx Power
#

import sys
import math
import argparse

from tail import *
from dwarf import *
from blinks import *


class cfg():

    debug            = 0
    verbose          = 0

    output           = None

    rpc_port         = 8912
    
    blink_count      = 1000000
    blink_delay      = 0.100
    blink_wait       = 1.0
    blink_interval   = 10

    window_length    = 100
    window_skip      = 10

DATA = {}


def dprint(level, *args, **kwargs):
    if cfg.debug >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)

def veprint(level, *args, **kwargs):
    if cfg.verbose >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)

def veprints(level, *args, **kwargs):
    if cfg.verbose >= level:
        print(*args, file=sys.stderr, end='', flush=True, **kwargs)


def print_csv(index,timex,period,Ravg,Tavg,Davg,Xavg,Favg,Pavg):
    if cfg.output is not None:
        msg  = time.strftime('%Y/%m/%d,%H:%M:%S')               # 0,1
        msg += ',{}'.format(index)                              # 2
        msg += ',{:.3f}'.format(timex)                          # 3
        msg += ',{:.3f}'.format(period)                         # 4
        msg += ',{:.3}'.format(Ravg)                            # 5
        msg += ',{:.3}'.format(Tavg)                            # 6
        msg += ',{:.3}'.format(Davg)                            # 7
        msg += ',{:.3}'.format(Xavg)                            # 8
        msg += ',{:.3}'.format(Favg)                            # 9
        msg += ',{:.3}'.format(Pavg)                            # 10
        msg += '\n'
        cfg.output.write(msg)


def estimate_xtal_ppm(blk, tx, rxs, devs, INDEX):

    OK = True

    DATA[INDEX] = {}
    DATA[INDEX]['TIME'] = blk.time()
    
    i1 = blk.blink(tx)
    blk.nap(cfg.blink_delay)
    i2 = blk.blink(tx)
    
    blk.wait_blinks((i1,i2), devs, cfg.blink_wait)
        
    Fcnt = 0
    Xsum = 0.0
    Fsum = 0.0
    Psum = 0.0
    Rsum = 0.0
    Tsum = 0.0
    
    for rx in rxs:
        try:
            key = rx.eui

            T1 = blk.get_hwts(i1, tx)
            R1 = blk.get_hwts(i1, rx)
            S1 = blk.get_swts(i1, rx)
            
            T2 = blk.get_hwts(i2, tx)
            R2 = blk.get_hwts(i2, rx)
            S2 = blk.get_swts(i2, rx)
            
            F1 = blk.get_xtal_ratio(i1, rx)
            F2 = blk.get_xtal_ratio(i2, rx)
            
            P1 = blk.get_rx_level(i1, rx)
            P2 = blk.get_rx_level(i2, rx)

            T21 = T2 - T1
            R21 = R2 - R1
            Xrt = (R21 - T21) / R21
            
            F12 = (F1 + F2) / 2
            P12 = (P1 + P2) / 2
            
            Pdb = RxPower2dBm(P12, cfg.prf)
            
            DATA[INDEX][key] = {}
            DATA[INDEX][key]['HWTx']  = T1
            DATA[INDEX][key]['HWRx']  = R1
            DATA[INDEX][key]['SWRx']  = S1
            DATA[INDEX][key]['Xrt']   = Xrt
            DATA[INDEX][key]['Pwr']   = P12
            DATA[INDEX][key]['Fpt']   = F12
            DATA[INDEX][key]['Pdb']   = Pdb

        except:
            OK = False

    return OK


def calculate_xtal_sync(blk, tx, rxs, devs, INDEX, START):

    t0 = DATA[START]['TIME']
    t1 = DATA[INDEX]['TIME']

    t = int(t1)
    h  = (t // 3600)
    m  = (t % 3600) // 60
    s  = t % 60
    
    period = t1 - t0
    
    veprint(1,'\n** BLINK #{} @ {}:{}:{} -- TIME:{:.3f}s PERIOD:{:.3f}s\n'.format(INDEX, h,m,s,t1,period))

    Fcnt = 0
    Xsum = 0.0
    Fsum = 0.0
    Psum = 0.0
    Rsum = 0.0
    Tsum = 0.0

    veprint(1,'    ANCHOR          Erx        Etx        Ediff      Eblks      Ettck      Pwr')
    veprint(1,'    ===============================================================================')
    
    for rx in rxs:
        try:
            key = rx.eui

            T0 = DATA[START][key]['HWTx']
            R0 = DATA[START][key]['HWRx']
            S0 = DATA[START][key]['SWRx']
            
            T1 = DATA[INDEX][key]['HWTx']
            R1 = DATA[INDEX][key]['HWRx']
            S1 = DATA[INDEX][key]['SWRx']
            
            Xrt = DATA[INDEX][key]['Xrt']
            Pwr = DATA[INDEX][key]['Pwr']
            Fpt = DATA[INDEX][key]['Fpt']
            Pdb = DATA[INDEX][key]['Pdb']
            
            T10 = T1 - T0
            R10 = R1 - R0
            S10 = S1 - S0
            
            XrtRxNtp = (R10 - S10) / S10
            XrtTxNtp = (T10 - S10) / S10
            
            Fcnt += 1
            Rsum += XrtRxNtp
            Tsum += XrtTxNtp
            Xsum += Xrt
            Fsum += Fpt
            Psum += Pwr

            msg = '    '
            msg += '{:<12s}  '.format(rx.host)
            msg += '{:7.3f}ppm '.format(XrtRxNtp*1E6)
            msg += '{:7.3f}ppm '.format(XrtTxNtp*1E6)
            msg += '{:7.3f}ppm '.format((XrtRxNtp-XrtTxNtp)*1E6)
            msg += '{:7.3f}ppm '.format(Xrt*1E6)
            msg += '{:7.3f}ppm '.format(Fpt*1E6)
            msg += '{:6.1f}dBm '.format(Pdb)
            
            veprint(1, msg)
                
        except (ZeroDivisionError,KeyError,IndexError):
            veprint(1,'    {:<12s}'.format(rx.host))


    Ravg = Rsum/Fcnt * 1E6
    Tavg = Tsum/Fcnt * 1E6
    Xavg = Xsum/Fcnt * 1E6
    Favg = Fsum/Fcnt * 1E6
    
    Pavg = Psum/Fcnt
    Pwr  = RxPower2dBm(Pavg,cfg.prf)

    print_csv(INDEX, t1, period, Ravg, Tavg, Ravg-Tavg, Xavg, Favg, Pwr)
                
    msg = '    AVERAGE       '
    msg += '{:7.3f}ppm '.format(Ravg)
    msg += '{:7.3f}ppm '.format(Tavg)
    msg += '{:7.3f}ppm '.format(Ravg-Tavg)
    msg += '{:7.3f}ppm '.format(Xavg)
    msg += '{:7.3f}ppm '.format(Favg)
    msg += '{:6.1f}dBm '.format(Pwr)

    veprint(1,'    ===============================================================================')
    veprint(1, msg)
        


def main():
    
    parser = argparse.ArgumentParser(description="XTAL NTP test")

    DW1000.add_device_arguments(parser)

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    parser.add_argument('-w', '--wait', type=float, default=cfg.blink_wait)
    parser.add_argument('-i', '--interval', type=float, default=cfg.blink_interval)
    parser.add_argument('-l', '--length', type=float, default=cfg.window_length)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('-s', '--skip', type=int, default=cfg.window_skip)
    parser.add_argument('-o', '--output', type=str, default=None)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    cfg.debug = args.debug
    cfg.verbose = args.verbose
    WPANFrame.verbosity = args.verbose

    if args.output is not None:
        cfg.output = open(args.output, 'w')
        
    cfg.blink_count    = args.count
    cfg.blink_delay    = args.delay
    cfg.blink_wait     = args.wait
    cfg.blink_interval = args.interval - args.delay
    cfg.window_skip    = args.skip
    cfg.window_length  = args.length

    ## Devices
    
    rpc = RPC()
    
    remotes  = [ ]
    xmitters = [ ]
    rceivers = [ ]
    
    for host in args.remote:
        try:
            star = host.startswith('*') or host.endswith('*')
            host = host.strip('*').rstrip('*')
            name = host.split('.')[0]
            anchor = DW1000(rpc,name,host,args.port)
            anchor.connect()
            remotes.append(anchor)
            if star:
                xmitters.append(anchor)
            else:
                rceivers.append(anchor)
        
        except (ValueError,ConnectionError) as err:
            raise RuntimeError(f'Remote host {host} not available: {err}')

    DW1000.handle_device_arguments(args,remotes)
    
    if args.verbose > 0:
        DW1000.print_all_remote_attrs(remotes,True)

    
    ## Run

    blk = Blinks(rpc)
    
    dut = xmitters[0]

    cfg.ch  = int(dut.get_dw1000_attr('channel'))
    cfg.prf = int(dut.get_dw1000_attr('prf'))

    try:
        while not estimate_xtal_ppm(blk, dut, rceivers, remotes, INDEX=0):
            eprint('First blink failed. Trying again.')
    
        for i in range(1, cfg.blink_count):
            blk.nap(cfg.blink_interval)
            try:
                estimate_xtal_ppm(blk, dut, rceivers, remotes, INDEX=i)
                start = max(0, i - cfg.window_length)
                window = i - start
                if window > cfg.window_skip:
                    calculate_xtal_sync(blk, dut, rceivers, remotes, INDEX=i, START=start)

            except (TimeoutError,ValueError,TypeError,KeyError,IndexError,ZeroDivisionError):
                eprint('Error. Continuing...')

    except KeyboardInterrupt:
        eprint('\nStopping...')
    except RuntimeError as err:
        errhandler('Runtime error', err)

    blk.stop()
    rpc.stop()


if __name__ == "__main__": main()

