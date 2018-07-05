#!/usr/bin/python3
#
# Test hack for developing RPi Tail algorithms
#

import argparse
import socket
import pprint
import math
import tail


class Config():

    blinks     = 100
    
    rpc_port   = 61666
    rpc_addr   = None

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
    
    parser.add_argument('-n', '--blinks', type=int, default=cfg.blinks)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('remotes', type=str, nargs='+', help="Remote addresses")
    
    args = parser.parse_args()

    remotes = [ ]
    
    for remote in args.remotes:
        addr = socket.getaddrinfo(remote, args.port, socket.AF_INET6)[0][4]
        remotes.append( { 'host': remote, 'addr': addr, 'EUI': None } )

    rpc_addr = [ rem['addr'] for rem in remotes ]
    rpc_bind = ('', args.port)

    rpc = tail.RPC(rpc_bind)
    blk = tail.Blinker(rpc)

    for addr in rpc_addr:
        rpc.setAttr(addr, 'txpsr', 256)
    
    for remote in remotes:
        addr = remote['addr']
        remote['EUI'] = rpc.getEUI(addr)
        print('DW1000 parameters @{} <{}>'.format(remote['host'],remote['EUI']))
        for attr in cfg.dw1000_attrs:
            val = rpc.getAttr(addr, attr)
            print('  {}={}'.format(attr, val))

    timer = tail.Timer()
    
    for i in range(args.blinks):
        for addr in rpc_addr:
            blk.Blink(addr)
            timer.nap(0.01)

    blk.stop()
    rpc.stop()

    ##
    ## Add analysis code here
    ##




if __name__ == "__main__":
    main()

