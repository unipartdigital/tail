#!/usr/bin/python3
#
# DW1000 attribute tool for Tail algorithm development
#

import argparse
import socket
import pprint
import tail

from tail import DW1000
from tail import eprint


class Config():

    rpc_port   = 61666

    
cfg = Config()


def main():
    
    parser = argparse.ArgumentParser(description="DW1000 attrbute tool")

    DW1000.AddParserOptions(parser)
    
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)

    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    remotes = [ ]
    
    for host in args.remote:
        addr = socket.getaddrinfo(host, args.port, socket.AF_INET6)[0][4]
        remotes.append( { 'host': host, 'addr': addr, 'EUI': None } )
    
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

    rpc.stop()


if __name__ == "__main__":
    main()

