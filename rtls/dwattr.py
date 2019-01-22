#!/usr/bin/python3
#
# DW1000 attribute tool for Tail algorithm development
#

import sys
import socket
import pprint
import argparse
import tail

from tail import DW1000
from tail import eprint

from config import *

VERBOSE = 0


def main():
    
    global VERBOSE
    
    parser = argparse.ArgumentParser(description="DW1000 attrbute tool")

    DW1000.AddParserArguments(parser)
    DW1000.AddPrintArguments(parser)
    
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('-s', '--summary', action='store_true', default=False)
    
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    VERBOSE = args.verbose
    
    rpc = tail.RPC(('',args.port))

    remotes = [ ]
    for host in args.remote:
        try:
            anchor = DW1000(host,args.port,rpc)
            remotes.append(anchor)
        except (ValueError,OSError,ConnectionRefusedError):
            eprint('Remote {} not accessible'.format(host))

    DW1000.HandleArguments(args,remotes)
    DW1000.HandlePrintArguments(args,remotes)

    if VERBOSE > 0:
        DW1000.PrintAllRemoteAttrs(remotes,args.summary)

    rpc.stop()


if __name__ == "__main__":
    main()

