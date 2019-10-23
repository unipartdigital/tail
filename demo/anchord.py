#!/usr/bin/python3
#
# One-way Ranging Anchor daemon
#

import os
import sys
import time
import json
import select
import socket
import netifaces
import argparse

from tail import *


class cfg():

    debug = 0

    dw1000_profile  = None
    dw1000_channel  = 5
    dw1000_pcode    = 12
    dw1000_prf      = 64
    dw1000_rate     = 850
    dw1000_txpsr    = 1024
    dw1000_smart    = 0
    dw1000_power    = '0x88888888'
    dw1000_txlevel  = -12.3

    if_name         = 'wpan0'

    anchor_addr     = ''
    anchor_port     = 8912

    server_host     = 'localhost'
    server_port     = 8913

    config_json     = '/etc/tail.json'


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def dprint(level, *args, **kwargs):
    if cfg.debug >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)


TAGS = { }

def register_tag(eui):
    TAGS[eui] = { 'EUI':eui, 'time':time.time(), }

def remove_tag(eui):
    TAGS.pop(eui, None)
    

def send_server_msg(tsock, **args):
    data = json.dumps(args)
    dprint(3, 'send_server_msg: {}'.format(data))
    tsock.sendto(data.encode(), cfg.server_raddr)

def recv_server_msg(tsock, rsock):
    (data,addr) = tsock.recvfrom(4096)
    dprint(3, 'recv_server_msg: {}'.format(data.decode()))
    mesg = json.loads(data.decode())
    Type = mesg.get('Type')
    if Type == 'FRAME':
        Data = mesg.get('Data')
        data = bytes.fromhex(Data)
        transmit_frame(rsock, data)
    elif Type == 'REGISTER':
        tag = mesg.get('Tag')
        register_tag(tag)
    elif Type == 'REMOVE':
        tag = mesg.get('Tag')
        remove_tag(tag)


def transmit_frame(rsock,frame):
    rsock.send(frame)

def transmit_beacon(rsock, ref):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(0xffff)
    frame.tail_protocol = 1
    frame.tail_frmtype = 1
    frame.tail_subtype = 0
    frame.tail_flags = 0
    frame.tail_beacon = bytes.fromhex(ref)
    rsock.send(frame.encode())


def recv_blink(tsock,rsock):
    (data,ancl,_,_) = rsock.recvmsg(4096, 1024, 0)
    frame = TailFrame(data,ancl)
    dprint(2, 'recv_blink: {}'.format(frame))
    if frame.tail_protocol == 1:
        anc = cfg.if_eui64
        src = frame.get_src_eui()
        send_server_msg(tsock, Type='RX', Anchor=anc, Src=src, TSInfo=dict(frame.timestamp.tsinfo), Frame=data.hex())
        if frame.tail_frmtype == 0:
            if src in TAGS:
                transmit_beacon(rsock,src)
                remove_tag(src)

def recv_times(tsock,rsock):
    (data,ancl,_,_) = rsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
    frame = TailFrame(data,ancl)
    dprint(2, 'recv_times: {}'.format(frame))
    if frame.tail_protocol == 1:
        anc = cfg.if_eui64
        send_server_msg(tsock, Type='TX', Anchor=anc, Src=anc, TSInfo=dict(frame.timestamp.tsinfo), Frame=data.hex())


def socket_loop():

    rsock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.PROTO_IEEE802154)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                         socket.SOF_TIMESTAMPING_RX_HARDWARE |
                         socket.SOF_TIMESTAMPING_TX_HARDWARE |
                         socket.SOF_TIMESTAMPING_RAW_HARDWARE |
                         socket.SOF_TIMESTAMPING_TX_SOFTWARE |
                         socket.SOF_TIMESTAMPING_RX_SOFTWARE |
                         socket.SOF_TIMESTAMPING_SOFTWARE)
    rsock.bind(cfg.if_bind)

    tsock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    tsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tsock.bind(cfg.anchor_laddr)

    socks = select.poll()
    socks.register(rsock, select.POLLIN)
    socks.register(tsock, select.POLLIN)

    while True:
        for (fd,flags) in socks.poll(1000):
            try:
                if fd == rsock.fileno():
                    if flags & select.POLLIN:
                        recv_blink(tsock,rsock)
                    if flags & select.POLLERR:
                        recv_times(tsock,rsock)
                elif fd == tsock.fileno():
                    if flags & select.POLLIN:
                        recv_server_msg(tsock,rsock)
                        
            except Exception as err:
                eprint('{}: {}'.format(err.__class__.__name__, err))
    
    socks.unregister(tsock)
    socks.unregister(rsock)

    tsock.close()
    rsock.close()


def main():

    parser = argparse.ArgumentParser(description="Tail anchor daemon")

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-I', '--interface', type=str, default=None)
    parser.add_argument('-s', '--server', type=str, default=None)
    parser.add_argument('-p', '--port', type=int, default=None)
    parser.add_argument('-c', '--config', type=str, default=None)
    parser.add_argument('--profile', type=str, default=None)
    parser.add_argument('--channel', type=int, default=None)
    parser.add_argument('--pcode', type=int, default=None)
    parser.add_argument('--prf', type=int, default=None)
    parser.add_argument('--rate', type=int, default=None)
    parser.add_argument('--txpsr', type=int, default=None)
    parser.add_argument('--power', type=str, default=None)
    
    args = parser.parse_args()

    if args.config:
        cfg.config_json = args.config

    with open(cfg.config_json, 'r') as f:
        cfg.config = json.load(f)

    for (key,value) in cfg.config.get('ANCHORD').items():
        try:
            getattr(cfg,key)
            setattr(cfg,key,value)
        except AttributeError:
            eprint('Invalid ANCHORD config {}: {}'.format(key,value))
            
    for (key,value) in cfg.config.get('DW1000').items():
        try:
            getattr(cfg,key)
            setattr(cfg,key,value)
        except AttributeError:
            eprint('Invalid DW1000 config {}: {}'.format(key,value))

    if args.debug:
        cfg.debug = args.debug
    if args.server:
        cfg.server_host = args.server
    if args.port:
        cfg.server_port = args.port
    if args.interface:
        cfg.if_name = args.interface
    if args.profile:
        cfg.dw1000_profile = args.profile
    if args.channel:
        cfg.dw1000_channel = args.channel
    if args.pcode:
        cfg.dw1000_pcode = args.pcode
    if args.prf:
        cfg.dw1000_prf = args.prf
    if args.txpsr:
        cfg.dw1000_txpsr = args.txpsr
    if args.power:
        cfg.dw1000_power = args.power
    if args.rate:
        cfg.dw1000_rate = args.rate
    
    WPANFrame.verbosity = max((0, cfg.debug - 2))

    cfg.if_bind  = (cfg.if_name, 0)

    addrs = netifaces.ifaddresses(cfg.if_name).get(netifaces.AF_PACKET)
    cfg.if_eui64 = addrs[0]['addr'].replace(':','')
    cfg.if_addr = bytes.fromhex(cfg.if_eui64)

    WPANFrame.set_ifaddr(cfg.if_addr)

    cfg.server_raddr = UDPTailPipe.get_saddr(cfg.server_host, cfg.server_port)[4]
    cfg.anchor_laddr = (cfg.anchor_addr, cfg.anchor_port, 0, 0)

    dprint(1, 'Tail Anchor daemon starting...')

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

