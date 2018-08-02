#!/usr/bin/python3
#
# Dump all incoming RPC Blink calls
#

import argparse
import socket
import pprint
import time
import tail

from tail import eprint

from config import *


def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")
    
    parser.add_argument('-p', '--port', type=int, default=RPC_PORT)
    
    args = parser.parse_args()

    rpc = tail.RPC(('',args.port))

    blk = tail.Blinker(rpc,[])
    rpc.register('blinkRecv', blk.BlinkDump)
    rpc.register('blinkXmit', blk.BlinkDump)

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()


if __name__ == "__main__":
    main()

