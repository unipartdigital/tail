#!/usr/bin/python3
#
# DW1000 attribute tool for Tail
#

import sys
import argparse

from tail import *
from blinks import *


def main():
    
    parser = argparse.ArgumentParser(description="DW1000 attribute tool")

    DW1000.add_device_arguments(parser)
    DW1000.add_print_arguments(parser)
    
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    parser.add_argument('-p', '--port', type=int, default=9812)
    parser.add_argument('remote', type=str, nargs='+', help="Remote address")
    
    args = parser.parse_args()
    
    rpc = RPC()
    
    remotes = []
    for host in args.remote:
        name = host.split('.')[0]
        try:
            anchor = DW1000(rpc, name, host, args.port)
            anchor.connect()
            remotes.append(anchor)
        except (ValueError,ConnectionError) as err:
            eprint(f'Remote {host} not accessible')

    DW1000.handle_device_arguments(args ,remotes)
    DW1000.handle_print_arguments(args, remotes)

    if args.verbose:
        DW1000.print_all_remote_attrs(remotes,True)

    rpc.stop()


if __name__ == "__main__": main()

