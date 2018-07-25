#!/usr/bin/python3
#
# Server/Tool template for developing RPi Tail algorithms
#

import argparse
import socket
import pprint
import math
import tail

from tail import eprint


class Config():

    blink_count = 100
    blink_delay = 0.1
    
    rpc_port   = 61666

    dw1000_attrs = {
        'channel'	  : 7,
        'rate'		  : 6800,
        'prf'		  : 256,
        'pcode'		  : 20,
        'txpsr'		  : 64,
        'antd'		  : 0x402c,
        'xtalt'		  : 0x0f,
        'smart_power'     : 1,
        'snr_threshold'   : 1,
        'fpr_threshold'   : 1,
        'noise_threshold' : 256,
    }
    

cfg = Config()


def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")
    
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    
    parser.add_argument('--reset', action='store_true', default=False)
    
    parser.add_argument('--channel',		type=str, default=None)
    parser.add_argument('--rate',		type=str, default=None)
    parser.add_argument('--prf',		type=str, default=None)
    parser.add_argument('--pcode',		type=str, default=None)
    parser.add_argument('--txpsr',		type=str, default=None)
    parser.add_argument('--antd',		type=str, default=None)
    parser.add_argument('--xtalt',		type=str, default=None)
    parser.add_argument('--smart_power',	type=str, default=None)
    parser.add_argument('--snr_threshold',	type=str, default=None)
    parser.add_argument('--fpr_threshold',	type=str, default=None)
    parser.add_argument('--noise_threshold',	type=str, default=None)

    parser.add_argument('remote', type=str, nargs='+', help="Remote address")

    args = parser.parse_args()

    blink_count = args.count
    blink_delay = args.delay

    remotes = [ ]
    
    for remote in args.remote:
        addr = socket.getaddrinfo(remote, args.port, socket.AF_INET6)[0][4]
        remotes.append( { 'host': remote, 'addr': addr, 'EUI': None } )

    rem_addr = [ rem['addr'] for rem in remotes ]
    
    rpc = tail.RPC(('', args.port))

    for remote in remotes:
        remote['EUI'] = rpc.getEUI(remote['addr'])
    
    if args.reset:
        for addr in rem_addr:
            for attr in cfg.dw1000_attrs:
                rpc.setAttr(addr, attr, cfg.dw1000_attrs[attr])

    for addr in rem_addr:
        if args.channel is not None:
            rpc.setAttr(addr, 'channel', args.channel)
        if args.rate is not None:
            rpc.setAttr(addr, 'rate', args.rate)
        if args.prf is not None:
            rpc.setAttr(addr, 'prf', args.prf)
        if args.pcode is not None:
            rpc.setAttr(addr, 'pcode', args.pcode)
        if args.txpsr is not None:
            rpc.setAttr(addr, 'txpsr', args.txpsr)
        if args.antd is not None:
            rpc.setAttr(addr, 'antd', int(args.antd,0))
        if args.xtalt is not None:
            rpc.setAttr(addr, 'xtalt', int(args.xtalt,0))
        if args.smart_power is not None:
            rpc.setAttr(addr, 'smart_power', args.smart_power)
        if args.snr_threshold is not None:
            rpc.setAttr(addr, 'snr_threshold', args.snr_threshold)
        if args.fpr_threshold is not None:
            rpc.setAttr(addr, 'fpr_threshold', args.fpr_threshold)
        if args.noise_threshold is not None:
            rpc.setAttr(addr, 'noise_threshold', args.noise_threshold)
    
    for remote in remotes:
        eprint('DW1000 attrs @{} <{}>'.format(remote['host'],remote['EUI']))
        for attr in cfg.dw1000_attrs:
            val = rpc.getAttr(remote['addr'], attr)
            eprint('  {:20s}: {}'.format(attr, val))

    blk = tail.Blinker(rpc,remotes)
    tmr = tail.Timer()

    try:
        for i in range(blink_count):
            for addr in rem_addr:
                timex = tmr.nap(blink_delay)
                index = blk.Blink(addr,timex)
            if i%100 == 0:
                eprint(end='.', flush=True)

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    eprint('\nDone')

    ##
    ## Add analysis code here
    ##




if __name__ == "__main__":
    main()

