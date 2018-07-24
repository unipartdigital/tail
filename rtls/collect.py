#!/usr/bin/python3
#
# Blink data collector for Tail algorithm development
#

import argparse
import socket
import pprint
import threading
import queue
import json
import math
import tail
import sys

import numpy as np
import numpy.linalg as lin

from numpy import dot

from tail import eprint


class Config():

    blink_time   = 1.0
    blink_delay  = 0.01
    blink_count  = 100
    
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


def getEUIs(blks,index,direc):
    euis = []
    if index is not None:
        if index in blks:
            for anc in blks[index]:
                if 'dir' in blks[index][anc]:
                    if blks[index][anc]['dir'] == direc:
                        euis.append(anc)
    return euis
                    

def getTS(blks,index,eui,direc):
    if blks[index][eui]['dir'] == direc:
        return blks[index][eui]['tss']
    raise ValueError
    

def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")

    parser.add_argument('-t', '--time', type=float, default=0)
    parser.add_argument('-d', '--delay', type=float, default=0)
    parser.add_argument('-n', '--blinks', type=int, default=0)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    
    parser.add_argument('--rate', type=int, default=cfg.dw1000_rate)
    parser.add_argument('--txpsr', type=int, default=cfg.dw1000_txpsr)
    parser.add_argument('--xtalt', type=str, default=None)
    parser.add_argument('--antd', type=str, default=None)
    
    parser.add_argument('remotes', type=str, nargs='+', help="Remote addresses")
    
    args = parser.parse_args()

    txs = [ ]
    rxs = [ ]
    
    for host in args.remotes:
        xmit = host.startswith('*') or host.endswith('*')
        host = host.strip('*').rstrip('*')
        addr = socket.getaddrinfo(host, args.port, socket.AF_INET6)[0][4]
        if xmit:
            txs.append( { 'host': host, 'addr': addr, 'EUI': None } )
        rxs.append( { 'host': host, 'addr': addr, 'EUI': None } )
    
    txs_addr = [ rem['addr'] for rem in txs ]
    rxs_addr = [ rem['addr'] for rem in rxs ]
    
    if args.time > 0:
        if args.delay > 0:
            blink_delay = args.delay
            blink_count = int(args.time / args.delay / len(txs))
        elif args.blinks > 0:
            blink_count = args.blinks // len(txs)
            blink_delay = args.time / args.blinks
        else:
            blink_delay = cfg.blink_delay
            blink_count = int(args.time / blink_delay / len(txs))
            
    elif args.delay > 0:
        blink_delay = args.delay
        if args.blinks > 0:
            blink_count = args.blinks // len(txs)
        else:
            blink_count = int(cfg.blink_time / blink_delay / len(txs))
            
    elif args.blinks > 0:
        blink_count = args.blinks // len(txs)
        blink_delay = cfg.blink_time / blink_count

    else:
        blink_count = cfg.blink_count // len(txs)
        blink_delay = cfg.blink_delay


    rpc = tail.RPC(('', args.port))

    for remote in rxs:
        remote['EUI'] = rpc.getEUI(remote['addr'])
        
    for addr in rxs_addr:
        rpc.setAttr(addr, 'rate', args.rate)
        rpc.setAttr(addr, 'txpsr', args.txpsr)
        if args.xtalt is not None:
            rpc.setAttr(addr, 'xtalt', int(args.xtalt,0))
        if args.antd is not None:
            rpc.setAttr(addr, 'antd', int(args.antd,0))
        
    for remote in rxs:
        addr = remote['addr']
        eprint('DW1000 parameters @{} <{}>'.format(remote['host'],remote['EUI']))
        for attr in cfg.dw1000_attrs:
            val = rpc.getAttr(addr, attr)
            eprint('  {}={}'.format(attr, val))

    
    blk = tail.Blinker(rpc,rxs)
    tmr = tail.Timer()

    done = 0
    index = 0

    eprint('Blinker starting')

    try:
        for i in range(blink_count):
        
            if i % 100 == 0:
                eprint(end='.', flush=True)
            
            for addr in txs_addr:
            
                timer = tmr.nap(blink_delay)
                index = blk.Blink(addr, timer)
                
                if index > 100:
                    done = index-100
                    blk.print(done)
    
        tmr.nap(1.0)

        for i in range(done,index):
            blk.print(i)

        eprint('\nDone')

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    

if __name__ == "__main__":
    main()

