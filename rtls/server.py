#!/usr/bin/python3
#
# Server/Tool template for developing RPi Tail algorithms
#

import argparse
import socket
import pprint
import math
import tail

from tail import DW1000
from tail import eprint


class Config():

    blink_count = 100
    blink_delay = 0.1
    
    rpc_port   = 61666


cfg = Config()


def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")
    
    DW1000.AddParserOptions(parser)
    
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)

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

    DW1000.HandleArguments(args,rpc,rem_addr)

    eprint('DW1000 Attributes:')
    
    for remote in remotes:
        eprint('\n{} <{}>'.format(remote['host'],remote['EUI']))
        DW1000.PrintRemoteAttrs(rpc,remote['addr'])

    eprint()


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

