#!/usr/bin/python3
#
# Blink data collector for Tail algorithm development
#

import sys
import math
import queue
import socket
import json
import argparse
import threading
import tail

import numpy as np
import numpy.linalg as lin

from numpy import dot
from pprint import pprint
from tail import eprint, DW1000
from config import *


class Config():

    blink_time   = 1.0
    blink_delay  = 0.01
    blink_count  = 100

CFG = Config()

VERBOSE = 0


pqueue = queue.Queue()

def print_id(index):
    pqueue.put(index)

def print_stop():
    pqueue.put(None)
    pqueue.join()

def print_blink(index, anchors, blinker):
    bs = blinker.blinks
    if index in bs:
        msg = '{},{}'.format(index,bs[index].get('__time__',''))
        for anc in anchors:
            eui = anc.eui
            if eui in bs[index]:
                TI = bs[index][eui]['tsi']
                if bs[index][eui]['dir'] == 'TX':
                    TX = bs[index][eui]['tss']
                    RX = ''
                else:
                    RX = bs[index][eui]['tss']
                    TX = ''
            else:
                RX = ''
                TX = ''
                TI = {}
            msg += ',{},{}'.format(TX,RX)
            for attr in DW1000_TSINFO_ATTRS:
                msg += ',{}'.format(TI.get(attr,''))
            print(msg)
        blinker.PurgeBlink(index)

def print_thread(blinker,anchors):
    while True:
        item = pqueue.get()
        pqueue.task_done()
        if item is None:
            break
        print_blink(item, anchors, blinker)



def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")

    DW1000.AddParserArguments(parser)
    
    parser.add_argument('-v', '--verbose', action='count')
    parser.add_argument('-t', '--time', type=float, default=0)
    parser.add_argument('-d', '--delay', type=float, default=0)
    parser.add_argument('-n', '--blinks', type=int, default=0)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    
    rpc = tail.RPC(('', args.port))

    txs = [ ]
    rxs = [ ]
    for host in args.remote:
        try:
            xmit = host.startswith('*') or host.endswith('*')
            host = host.strip('*').rstrip('*')
            remo = DW1000(host,args.port,rpc)
            rxs.append(remo)
            if xmit:
                txs.append(remo)
        except:
            eprint('Remote {} exist does not'.format(host))

    
    if args.time > 0:
        if args.delay > 0:
            blink_delay = args.delay
            blink_count = int(args.time / args.delay / len(txs))
        elif args.blinks > 0:
            blink_count = args.blinks // len(txs)
            blink_delay = args.time / args.blinks
        else:
            blink_delay = CFG.blink_delay
            blink_count = int(args.time / blink_delay / len(txs))

    elif args.delay > 0:
        blink_delay = args.delay
        if args.blinks > 0:
            blink_count = args.blinks // len(txs)
        else:
            blink_count = int(CFG.blink_time / blink_delay / len(txs))

    elif args.blinks > 0:
        blink_count = args.blinks // len(txs)
        blink_delay = CFG.blink_time / blink_count

    else:
        blink_count = CFG.blink_count // len(txs)
        blink_delay = CFG.blink_delay


    DW1000.HandleArguments(args,rxs)

    if VERBOSE:
        DW1000.PrintAllRemoteAttrs(rxs)

    blk = tail.Blinker(rpc,rxs)
    tmr = tail.Timer()

    thr = threading.Thread(target=print_thread, kwargs={'blinker':blk,'anchors':rxs})
    thr.start()

    done = 0
    index = 0

    eprint('Blinker starting')

    try:
        for i in range(blink_count):
            
            for remo in txs:
            
                timer = tmr.nap(blink_delay)
                index = blk.Blink(remo.addr,timer)
                
                done = index-100
                print_id(done)
                
            if i % 100 == 0:
                eprint(end='.', flush=True)
            
        tmr.nap(1)

        for i in range(done,index):
            print_id(i)

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()

    print_stop()
    
    eprint('\nDone')
    

if __name__ == "__main__":
    main()

