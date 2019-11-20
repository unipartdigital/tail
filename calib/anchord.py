#!/usr/bin/python3
#
# Tail Anchor daemon prototype
#

import os
import sys
import time
import json
import select
import socket
import netifaces
import argparse
import traceback

from tail import *


class cfg:

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

    server_host     = None
    server_port     = 8913

    config_json     = '/etc/tail.json'


class socks:

    poll = None
    
    rsock = None
    upipe = None
    tpipe = None

    udp_addrs = {}
    udp_pipes = {}
    
    tcp_clients = {}



def dprint(level, *args, **kwargs):
    if cfg.debug >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)


def register_tag(eui):
    cfg.tags[eui] = { 'EUI':eui, 'time':time.time(), }

def remove_tag(eui):
    cfg.tags.pop(eui, None)
    

def register_udp_client(owner,addr,port):
    pipe = UDPTailPipe.clone(socks.upipe)
    pipe.connect(addr,port)
    socks.udp_pipes[owner] = pipe
    socks.udp_addrs[pipe.remote] = pipe
    dprint(2, 'register_udp_client {}'.format(pipe.remote))

def unregister_udp_client(owner):
    if owner in socks.udp_pipes:
        pipe = socks.udp_pipes.pop(owner)
        socks.udp_addrs.pop(pipe.remote,None)
        dprint(2, 'unregister_udp_client {}'.format(pipe.remote))

def send_udp_client(**args):
    mesg = json.dumps(args)
    for pipe in socks.udp_pipes.values():
        pipe.sendmsg(mesg)
        dprint(3, 'send_udp_client: {} to {}'.format(mesg,pipe.remote))

def recv_udp_client(pipe):
    try:
        pipe.fillbuf()
        while pipe.hasmsg():
            (data,addr) = pipe.getmsgfrom()
            if addr in socks.udp_addrs:
                mesg = json.loads(data)
                recv_client_msg(socks.udp_addrs[addr], mesg)
    except Exception as err:
        errhandler('recv_udp_client: Unable to receive', err)


def register_tcp_client(pipe):
    socks.poll.register(pipe.sock, select.POLLIN)
    socks.tcp_clients[pipe.fileno()] = pipe
    
def unregister_tcp_client(pipe):
    if pipe.fileno() in socks.tcp_clients:
        unregister_udp_client(pipe)
        socks.poll.unregister(pipe.sock)
        socks.tcp_clients.pop(pipe.fileno())
        pipe.close()

def send_tcp_client(pipe, **args):
    mesg = json.dumps(args)
    dprint(2, 'send_tcp_client: {}'.format(mesg))
    try:
        pipe.sendmsg(mesg)
    except ConnectionError:
        unregister_tcp_client(pipe)
        
def recv_tcp_client(pipe):
    try:
        pipe.fillbuf()
        while pipe.hasmsg():
            data = pipe.getmsg()
            mesg = json.loads(data)
            recv_client_msg(pipe, mesg)
    except ConnectionError:
        unregister_tcp_client(pipe)


def recv_client_msg(pipe, mesg):
    dprint(3, 'recv_client_msg: {}'.format(mesg))
    Type = mesg.get('Type')
    if Type == 'FRAME':
        Data = mesg.get('Data')
        data = bytes.fromhex(Data)
        transmit_wpan_frame(data)
    elif Type == 'BEACON':
        bid = mesg.get('Beacon')
        sub = mesg.get('SubType')
        transmit_wpan_beacon(bid, sub)
    elif Type == 'REGISTER':
        tag = mesg.get('Tag')
        register_tag(tag)
    elif Type == 'REMOVE':
        tag = mesg.get('Tag')
        remove_tag(tag)
    elif Type == 'UDP':
        if isinstance(pipe,TCPTailPipe):
            port = mesg.get('Port')
            register_udp_client(pipe, pipe.remote[0], port)
    elif Type == 'NOUDP':
        if isinstance(pipe,TCPTailPipe):
            unregister_udp_client(pipe)
    elif Type == 'RPC':
        if isinstance(pipe,TCPTailPipe):
            recv_client_rpc(pipe,mesg)
    else:
        eprint('Unknown message received: {}'.format(mesg))

def recv_client_rpc(pipe, mesg):
    Seqn = mesg.get('Seqn')
    Func = mesg.get('Func')
    Args = mesg.get('Args')
    if Func == 'GETEUI':
        Args['Value'] = cfg.if_eui64
        send_tcp_client(pipe, Type='RPC', Seqn=Seqn, Func=Func, Args=Args)
    elif Func == 'GETDTATTR':
        Args['Value'] = GetDTAttr(Args['Attr'],Args['Format'])
        send_tcp_client(pipe, Type='RPC', Seqn=Seqn, Func=Func, Args=Args)
    elif Func == 'GETDWATTR':
        Args['Value'] = GetDWAttr(Args['Attr'])
        send_tcp_client(pipe, Type='RPC', Seqn=Seqn, Func=Func, Args=Args)
    elif Func == 'SETDWATTR':
        SetDWAttr(Args['Attr'], Args['Value'])
        Args['Value'] = GetDWAttr(Args['Attr'])
        send_tcp_client(pipe, Type='RPC', Seqn=Seqn, Func=Func, Args=Args)
    else:
        eprint('Unknown RPC message received: {}'.format(mesg))


def transmit_wpan_frame(frame):
    socks.rsock.send(frame)

def transmit_wpan_beacon(ref, sub=0, flags=0):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(0xffff)
    frame.tail_protocol = 1
    frame.tail_frmtype = 1
    frame.tail_subtype = sub
    frame.tail_flags = flags
    frame.tail_beacon = bytes.fromhex(ref)
    socks.rsock.send(frame.encode())


def recv_blink():
    (data,ancl,_,_) = socks.rsock.recvmsg(4096, 1024, 0)
    frame = TailFrame(data,ancl)
    dprint(4, 'recv_blink: {}'.format(frame))
    if frame.tail_protocol == 1:
        anc = cfg.if_eui64
        src = frame.get_src_eui()
        if frame.timestamp is None:
            eprint('RX frame timestamp missing ANC:{} ANCL:{} FRAME:{}'.format(anc,ancl,frame))
        elif frame.timestamp.tsinfo.rawts == 0 or frame.timestamp.hires == 0:
            eprint('RX frame timestamp invalid ANC:{} ANCL:{} FRAME:{}'.format(anc,ancl,frame))
        tms = { 'swts': int(frame.timestamp.sw), 'hwts': int(frame.timestamp.hw), 'hires': int(frame.timestamp.hires) }
        tsi = dict(frame.timestamp.tsinfo)
        send_udp_client(Type='RX', Anchor=anc, Src=src, Times=tms, TSInfo=tsi, Frame=data.hex())
        if frame.tail_frmtype == 0:
            if src in cfg.tags:
                transmit_wpan_beacon(src)
                remove_tag(src)

def recv_times():
    (data,ancl,_,_) = socks.rsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
    frame = TailFrame(data,ancl)
    dprint(4, 'recv_times: {}'.format(frame))
    if frame.tail_protocol == 1:
        anc = cfg.if_eui64
        if frame.timestamp is None:
            eprint('TX frame timestamp missing ANC:{} ANCL:{} FRAME:{}'.format(anc,ancl,frame))
        elif frame.timestamp.tsinfo.rawts == 0 or frame.timestamp.hires == 0:
            eprint('TX frame timestamp invalid ANC:{} ANCL:{} FRAME:{}'.format(anc,ancl,frame))
        tms = { 'swts': int(frame.timestamp.sw), 'hwts': int(frame.timestamp.hw), 'hires': int(frame.timestamp.hires) }
        tsi = dict(frame.timestamp.tsinfo)
        send_udp_client(Type='TX', Anchor=anc, Src=anc, Times=tms, TSInfo=tsi, Frame=data.hex())


def socket_loop():

    socks.poll = select.poll()
    
    socks.rsock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.PROTO_IEEE802154)
    socks.rsock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                         socket.SOF_TIMESTAMPING_RX_HARDWARE |
                         socket.SOF_TIMESTAMPING_TX_HARDWARE |
                         socket.SOF_TIMESTAMPING_RAW_HARDWARE |
                         socket.SOF_TIMESTAMPING_RX_SOFTWARE |
                         socket.SOF_TIMESTAMPING_SOFTWARE)
    socks.rsock.bind((cfg.if_name,0))
    socks.poll.register(socks.rsock, select.POLLIN)
    rfd = socks.rsock.fileno()

    socks.upipe = UDPTailPipe()
    socks.upipe.listen(cfg.anchor_addr, cfg.anchor_port)
    socks.poll.register(socks.upipe.sock, select.POLLIN)
    ufd = socks.upipe.fileno()

    socks.tpipe = TCPTailPipe()
    socks.tpipe.listen(cfg.anchor_addr, cfg.anchor_port)
    socks.poll.register(socks.tpipe.sock, select.POLLIN)
    tfd = socks.tpipe.fileno()

    if cfg.server_host is not None:
        register_udp_client(socks.upipe, cfg.server_host, cfg.server_port)

    while True:
        for (fd,flags) in socks.poll.poll():
            try:
                if fd == rfd:
                    if flags & select.POLLIN:
                        recv_blink()
                    if flags & select.POLLERR:
                        recv_times()
                elif fd == ufd:
                    if flags & select.POLLIN:
                        recv_udp_client(socks.upipe)
                elif fd in socks.tcp_clients:
                    if flags & select.POLLIN:
                        recv_tcp_client(socks.tcp_clients[fd])
                elif fd == tfd:
                    if flags & select.POLLIN:
                        register_tcp_client(socks.tpipe.accept())

            except BlockingIOError as err:
                errhandler('Problem with WPAN interface',err)
                raise SystemExit

            except Exception as err:
                eprint('{}: {}'.format(err.__class__.__name__, err))
    


def main():

    parser = argparse.ArgumentParser(description="Tail anchor daemon")

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-v', '--verbose', action='count', default=0)
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

    WPANFrame.verbosity = args.verbose
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
    
    cfg.if_addr  = GetDTAttrRaw('decawave,eui64')
    cfg.if_eui64 = cfg.if_addr.hex()
    WPANFrame.set_ifaddr(cfg.if_addr)

    cfg.tags = {}

    dprint(1, 'Tail Anchor <{}> daemon starting...'.format(cfg.if_eui64))

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

