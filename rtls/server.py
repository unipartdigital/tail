#!/usr/bin/python3
#
# Test hack for developing RPi Tail algorithms
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

    dw1000_rate  = 6800
    dw1000_txpsr = 256
    dw1000_xtalt = 0x0f
    dw1000_antd  = 0x402c

    dw1000_attrs = (
        'snr_threshold',
        'fpr_threshold',
        'noise_threshold',
        'channel',
        'pcode',
        'txpsr',
        'prf',
        'rate',
        'antd',
        'xtalt',
        'smart_power',
    )


cfg = Config()


def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")
    
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('remotes', type=str, nargs='+', help="Remote addresses")
    
    parser.add_argument('--rate', type=int, default=cfg.dw1000_rate)
    parser.add_argument('--txpsr', type=int, default=cfg.dw1000_txpsr)
    parser.add_argument('--xtalt', type=str, default=None)
    parser.add_argument('--antd', type=str, default=None)
    
    args = parser.parse_args()

    blink_count = args.count
    blink_delay = args.delay

    remotes = [ ]
    
    for remote in args.remotes:
        addr = socket.getaddrinfo(remote, args.port, socket.AF_INET6)[0][4]
        remotes.append( { 'host': remote, 'addr': addr, 'EUI': None } )

    rem_addr = [ rem['addr'] for rem in remotes ]
    
    rpc = tail.RPC(('', args.port))

    for remote in remotes:
        remote['EUI'] = rpc.getEUI(remote['addr'])
        
    for addr in rem_addr:
        rpc.setAttr(addr, 'rate', args.rate)
        rpc.setAttr(addr, 'txpsr', args.txpsr)
        if args.xtalt is not None:
            rpc.setAttr(addr, 'xtalt', int(args.xtalt,0))
        if args.antd is not None:
            rpc.setAttr(addr, 'antd', int(args.antd,0))
        
    for remote in remotes:
        addr = remote['addr']
        eprint('DW1000 parameters @{} <{}>'.format(remote['host'],remote['EUI']))
        for attr in cfg.dw1000_attrs:
            val = rpc.getAttr(addr, attr)
            eprint('  {}={}'.format(attr, val))

    blk = tail.Blinker(rpc,remotes)
    tmr = tail.Timer()

    try:
        for i in range(blink_count):
            for addr in rem_addr:
                time = tmr.nap(blink_delay)
                index = blk.Blink(addr,time)
                eprint(end='.', flush=True)

        eprint('\nDone')

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    ##
    ## Add analysis code here
    ##




if __name__ == "__main__":
    main()

