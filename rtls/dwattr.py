#!/usr/bin/python3
#
# DW1000 attribute tool for Tail algorithm development
#

import argparse
import socket
import pprint
import tail

from tail import eprint


class Config():

    rpc_port   = 61666

    dw1000_attrs = (
        'channel',
        'rate',
        'prf',
        'pcode',
        'txpsr',
        'antd',
        'xtalt',
        'smart_power',
        'snr_threshold',
        'fpr_threshold',
        'noise_threshold',
    )

    dw1000_defaults = {
        'channel'	  : 7,
        'rate'		  : 6800,	
        'prf'		  : 64,
        'pcode'		  : 20,
        'txpsr'		  : 64,
        'antd'		  : 0x4028,
        'xtalt'		  : 0x0f,
        'smart_power'     : 1,
        'snr_threshold'   : 1,
        'fpr_threshold'   : 1,
        'noise_threshold' : 256,
    }
    

cfg = Config()


def main():
    
    parser = argparse.ArgumentParser(description="DW1000 attrbute tool")

    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    
    parser.add_argument('--reset', action='store_true', default=False)
    
    parser.add_argument('--channel',		type=str, default=None)
    parser.add_argument('--rate',		type=str, default=None)
    parser.add_argument('--prf',		type=str, default=None)
    parser.add_argument('--pcode',		type=str, default=None)
    parser.add_argument('--txpsr',		type=str, default=None)
    parser.add_argument('--antd',		type=str, default=None)
    parser.add_argument('--xtalt',		type=str, default=None)
    parser.add_argument('--smart_power',	type=str, default=None)
    parser.add_argument('--snr_threshold',	type=str, default=None)
    parser.add_argument('--fpr_threshold',	type=str, default=None)
    parser.add_argument('--noise_threshold',	type=str, default=None)
    
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

    if args.reset:
        for addr in rem_addr:
            for attr in cfg.dw1000_defaults:
                rpc.setAttr(addr, attr, cfg.dw1000_defaults[attr])

    for addr in rem_addr:
        if args.channel is not None:
            rpc.setAttr(addr, 'channel', args.channel)
        if args.rate is not None:
            rpc.setAttr(addr, 'rate', args.rate)
        if args.prf is not None:
            rpc.setAttr(addr, 'prf', args.prf)
        if args.pcode is not None:
            rpc.setAttr(addr, 'pcode', args.pcode)
        if args.txpsr is not None:
            rpc.setAttr(addr, 'txpsr', args.txpsr)
        if args.antd is not None:
            rpc.setAttr(addr, 'antd', int(args.antd,0))
        if args.xtalt is not None:
            rpc.setAttr(addr, 'xtalt', int(args.xtalt,0))
        if args.smart_power is not None:
            rpc.setAttr(addr, 'smart_power', args.smart_power)
        if args.snr_threshold is not None:
            rpc.setAttr(addr, 'snr_threshold', args.snr_threshold)
        if args.fpr_threshold is not None:
            rpc.setAttr(addr, 'fpr_threshold', args.fpr_threshold)
        if args.noise_threshold is not None:
            rpc.setAttr(addr, 'noise_threshold', args.noise_threshold)
    
    
    print('DW1000 Attributes:')
    
    for remote in remotes:
        print('\n{} <{}>'.format(remote['host'],remote['EUI']))
        for attr in cfg.dw1000_attrs:
            val = rpc.getAttr(remote['addr'], attr)
            print('  {:20s}: {}'.format(attr, val))

    rpc.stop()

    print()


if __name__ == "__main__":
    main()

