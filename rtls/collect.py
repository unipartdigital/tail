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

from tail import DW1000
from tail import eprint


class Config():

    blink_time   = 1.0
    blink_delay  = 0.01
    blink_count  = 100

    rpc_port   = 61666


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

    DW1000.AddParserOptions(parser)
    
    parser.add_argument('-t', '--time', type=float, default=0)
    parser.add_argument('-d', '--delay', type=float, default=0)
    parser.add_argument('-n', '--blinks', type=int, default=0)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    txs = [ ]
    rxs = [ ]
    
    for host in args.remote:
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

    DW1000.HandleArguments(args,rpc,rxs_addr)

    eprint('DW1000 Attributes:')
    
    for remote in rxs:
        eprint('\n{} <{}>'.format(remote['host'],remote['EUI']))
        DW1000.PrintRemoteAttrs(rpc,remote['addr'])

    eprint()

    
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
                index = blk.Blink(addr,timer)
                
                if index > 100:
                    done = index-100
                    blk.print(done)
    
        tmr.nap(0.1)

        for i in range(done,index):
            blk.print(i)

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    eprint('\nDone')
    

if __name__ == "__main__":
    main()

