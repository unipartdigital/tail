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
    
    parser.add_argument('-v', '--verbose', action='count', default=1)
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()

    VERBOSE = args.verbose
    
    rpc = tail.RPC(('',args.port))

    remotes = [ ]
    for host in args.remote:
        try:
            anchor = DW1000(host,args.port,rpc)
            remotes.append(anchor)
        except:
            eprint('Remote {} exist does not'.format(host))

    DW1000.HandleArguments(args,remotes)
    
    if VERBOSE > 0:
        DW1000.PrintAllRemoteAttrs(remotes)

    rpc.stop()


if __name__ == "__main__":
    main()
