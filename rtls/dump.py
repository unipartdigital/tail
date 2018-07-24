#!/usr/bin/python3
#
# Dump all incoming RPC Blink calls
#

import argparse
import socket
import pprint
import math
import tail

from tail import eprint


class Config():

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


def main():
    
    parser = argparse.ArgumentParser(description="RTLS server")
    
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    
    parser.add_argument('--rate', type=int, default=cfg.dw1000_rate)
    parser.add_argument('--txpsr', type=int, default=cfg.dw1000_txpsr)
    parser.add_argument('--xtalt', type=str, default=None)
    parser.add_argument('--antd', type=str, default=None)
    
    args = parser.parse_args()

    rpc = tail.RPC(('', args.port))

    blk = tail.Blinker(rpc,[])
    rpc.register('blinkRecv', blk.BlinkDump)
    rpc.register('blinkXmit', blk.BlinkDump)

    tmr = tail.Timer()

    try:
        while True:
            pass

        eprint('\nDone')

    except KeyboardInterrupt:
        eprint('\nStopping...')

    blk.stop()
    rpc.stop()


if __name__ == "__main__":
    main()

