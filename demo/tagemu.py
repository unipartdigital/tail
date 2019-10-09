#!/usr/bin/python3

import os
import sys
import time
import math
import socket
import select
import argparse
import netifaces
import configparser

from tail import *


class cfg():

    debug = 0

    dw1000_profile  = None
    dw1000_channel  = 5
    dw1000_pcode    = 12
    dw1000_prf      = 64
    dw1000_rate     = 850
    dw1000_txpsr    = 1024
    dw1000_power    = 0x88888888
    dw1000_smart    = 0

    if_name         = 'wpan0'
    if_addr         = None
    if_eui64        = None
    
    blink_delay     = 0.020
    blink_interval  = 1.000
    blink_count     = None
    
CONFIG_FILE = '/etc/tail.conf'


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def dprint(level, *args, **kwargs):
    if cfg.debug > level:
        print(*args, file=sys.stderr, flush=True, **kwargs)


def transmit_blink(rsock):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(0xffff)
    frame.tail_protocol = 1
    frame.tail_frmtype = 0
    data = frame.encode()
    dprint(2, 'transmit_blink: {}'.format(frame))
    rsock.send(data)


def transmit_ranging_resp(rsock):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(0xffff)
    frame.tail_protocol = 1
    frame.tail_frmtype = 3
    frame.tail_owr = True
    frame.tail_txtime = 0
    data = frame.encode()
    dprint(2, 'transmit_ranging_resp: {}'.format(frame))
    rsock.send(data)


def socket_loop():

    rsock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.PROTO_IEEE802154)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                     socket.SOF_TIMESTAMPING_RX_HARDWARE |
                     socket.SOF_TIMESTAMPING_TX_HARDWARE |
                     socket.SOF_TIMESTAMPING_RAW_HARDWARE)
    rsock.bind(cfg.if_bind)

    count = 0
    
    try:
        while True:
            transmit_blink(rsock);
            time.sleep(cfg.blink_delay)
            transmit_ranging_resp(rsock);
            time.sleep(cfg.blink_interval)
            
            count += 1
            if cfg.blink_count and count > cfg.blink_count:
                break
    
    except KeyboardInterrupt:
        print('Exiting...')

    rsock.close()


def main():

    if False: #os.path.exists(CONFIG_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            for key,val in config['tagemu'].items():
                setattr(cfg,key,val)
        except Exception as err:
            eprint('Could not read config file {}: {}'.format(CONFIG_FILE, err))
    
    parser = argparse.ArgumentParser(description="uTrack Connector daemon")

    parser.add_argument('-D', '--debug', action='count', default=cfg.debug)
    parser.add_argument('-I', '--interface', type=str, default=cfg.if_name)
    parser.add_argument('-c', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-i', '--interval', type=float, default=cfg.blink_interval)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    parser.add_argument('--profile', type=str, default=cfg.dw1000_profile)
    parser.add_argument('--channel', type=int, default=cfg.dw1000_channel)
    parser.add_argument('--pcode', type=int, default=cfg.dw1000_pcode)
    parser.add_argument('--prf', type=int, default=cfg.dw1000_prf)
    parser.add_argument('--rate', type=int, default=cfg.dw1000_rate)
    parser.add_argument('--txpsr', type=int, default=cfg.dw1000_txpsr)
    parser.add_argument('--power', type=str, default=cfg.dw1000_power)
    
    args = parser.parse_args()

    cfg.debug = args.debug
    WPANFrame.verbosity = max((0, args.debug - 1))

    cfg.blink_count = args.count
    cfg.blink_delay = args.delay
    cfg.blink_interval = args.interval
    
    cfg.if_name  = args.interface
    cfg.if_bind  = (cfg.if_name, 0)

    addrs = netifaces.ifaddresses(cfg.if_name).get(netifaces.AF_PACKET)
    cfg.if_eui64 = addrs[0]['addr'].replace(':','')
    cfg.if_addr = bytes.fromhex(cfg.if_eui64)

    WPANFrame.set_ifaddr(cfg.if_addr)

    cfg.dw1000_profile = args.profile
    cfg.dw1000_channel = args.channel
    cfg.dw1000_pcode = args.pcode
    cfg.dw1000_prf = args.prf
    cfg.dw1000_txpsr = args.txpsr
    cfg.dw1000_power = args.power
    cfg.dw1000_rate = args.rate

    try:
        SetDWAttr('channel', cfg.dw1000_channel)
        SetDWAttr('pcode', cfg.dw1000_pcode)
        SetDWAttr('prf', cfg.dw1000_prf)
        SetDWAttr('rate', cfg.dw1000_rate)
        SetDWAttr('txpsr', cfg.dw1000_txpsr)
        SetDWAttr('smart_power', cfg.dw1000_smart)
        SetDWAttr('tx_power', cfg.dw1000_power)

        if cfg.dw1000_profile:
            SetDWAttr('profile', cfg.dw1000_profile)

        socket_loop()

    except KeyboardInterrupt:
        dprint(1, 'Exiting...')


if __name__ == "__main__": main()

