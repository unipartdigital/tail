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

    server_host     = None
    server_port     = 8913

    config_json     = '/etc/tail.json'


def dprint(level, *args, **kwargs):
    if cfg.debug >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)


TAGS = { }

def register_tag(eui):
    TAGS[eui] = { 'EUI':eui, 'time':time.time(), }

def remove_tag(eui):
    TAGS.pop(eui, None)
    

CLIENTS = {}
CLIPOLL = select.poll()

def accept_client(pipe):
    CLIPOLL.register(pipe.sock, select.POLLIN)
    CLIENTS[pipe.sock.fileno()] = pipe

def remove_client(pipe):
    CLIPOLL.unregister(pipe.sock)
    del CLIENTS[pipe.sock.fileno()]
    pipe.close()

def client_sendmsg(pipe,mesg):
    try:
        pipe.sendmsg(mesg)
    except ConnectionError:
        remove_client(pipe)

def client_recvmsg(pipe):
    try:
        pipe.fillmsg()
    except ConnectionError:
        remove_client(pipe)


def send_client_bcast(**args):
    mesg = json.dumps(args)
    dprint(3, f'send_client_bcast: {mesg}')
    for pipe in list(CLIENTS.values()):
        client_sendmsg(pipe,mesg)

def send_client_msg(pipe, **args):
    mesg = json.dumps(args)
    dprint(3, f'send_client_msg: {mesg}')
    pipe.sendmsg(mesg)

def recv_client_msg(pipe, rsock):
    client_recvmsg(pipe)
    while pipe.hasmsg():
        data = pipe.getmsg()
        mesg = json.loads(data)
        dprint(3, f'recv_client_msg: {mesg}')
        Type = mesg.get('Type')
        if Type == 'FRAME':
            Data = mesg.get('Data')
            data = bytes.fromhex(Data)
            transmit_frame(rsock, data)
        elif Type == 'BEACON':
            bid = mesg.get('Beacon')
            sub = mesg.get('SubType')
            transmit_beacon(rsock, bid, sub)
        elif Type == 'REGISTER':
            tag = mesg.get('Tag')
            register_tag(tag)
        elif Type == 'REMOVE':
            tag = mesg.get('Tag')
            remove_tag(tag)
        elif Type == 'RPC':
            recv_client_rpc(pipe,rsock,mesg)
        else:
            eprint(f'Unknown server message received: {mesg}')

def recv_client_rpc(pipe, rsock, mesg):
    Seqn = mesg.get('Seqn')
    Func = mesg.get('Func')
    Args = mesg.get('Args')
    if Func == 'GETEUI':
        Args['Value'] = cfg.if_eui64
        send_client_msg(pipe, Type='RPC', Seqn=Seqn, Func=Func, Args=Args)
    elif Func == 'GETDTATTR':
        Args['Value'] = GetDTAttr(Args['Attr'],Args['Format'])
        send_client_msg(pipe, Type='RPC', Seqn=Seqn, Func=Func, Args=Args)
    elif Func == 'GETDWATTR':
        Args['Value'] = GetDWAttr(Args['Attr'])
        send_client_msg(pipe, Type='RPC', Seqn=Seqn, Func=Func, Args=Args)
    elif Func == 'SETDWATTR':
        SetDWAttr(Args['Attr'], Args['Value'])
        Args['Value'] = GetDWAttr(Args['Attr'])
        send_client_msg(pipe, Type='RPC', Seqn=Seqn, Func=Func, Args=Args)
    else:
        eprint(f'Unknown RPC message received: {mesg}')


def transmit_frame(rsock, frame):
    rsock.send(frame)

def transmit_beacon(rsock, ref, sub=0, flags=0):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(0xffff)
    frame.tail_protocol = 1
    frame.tail_frmtype = 1
    frame.tail_subtype = sub
    frame.tail_flags = flags
    frame.tail_beacon = bytes.fromhex(ref)
    rsock.send(frame.encode())


def recv_blink(rsock):
    (data,ancl,_,_) = rsock.recvmsg(4096, 1024, 0)
    frame = TailFrame(data,ancl)
    dprint(2, f'recv_blink: {frame}')
    if frame.tail_protocol == 1:
        anc = cfg.if_eui64
        src = frame.get_src_eui()
        if frame.timestamp is None:
            eprint(f'RX frame timestamp missing ANC:{anc} ANCL:{ancl} FRAME:{frame}')
        elif frame.timestamp.tsinfo.rawts == 0 or frame.timestamp.hires == 0:
            eprint(f'RX frame timestamp invalid ANC:{anc} ANCL:{ancl} FRAME:{frame}')
        tms = { 'swts': int(frame.timestamp.sw), 'hwts': int(frame.timestamp.hw), 'hires': int(frame.timestamp.hires) }
        tsi = dict(frame.timestamp.tsinfo)
        send_client_bcast(Type='RX', Anchor=anc, Src=src, Times=tms, TSInfo=tsi, Frame=data.hex())
        if frame.tail_frmtype == 0:
            if src in TAGS:
                transmit_beacon(rsock,src)
                remove_tag(src)

def recv_times(rsock):
    (data,ancl,_,_) = rsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
    frame = TailFrame(data,ancl)
    dprint(2, f'recv_times: {frame}')
    if frame.tail_protocol == 1:
        anc = cfg.if_eui64
        if frame.timestamp is None:
            eprint(f'TX frame timestamp missing ANC:{anc} ANCL:{ancl} FRAME:{frame}')
        elif frame.timestamp.tsinfo.rawts == 0 or frame.timestamp.hires == 0:
            eprint(f'TX frame timestamp invalid ANC:{anc} ANCL:{ancl} FRAME:{frame}')
        tms = { 'swts': int(frame.timestamp.sw), 'hwts': int(frame.timestamp.hw), 'hires': int(frame.timestamp.hires) }
        tsi = dict(frame.timestamp.tsinfo)
        send_client_bcast(Type='TX', Anchor=anc, Src=anc, Times=tms, TSInfo=tsi, Frame=data.hex())


def socket_loop():

    rsock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.PROTO_IEEE802154)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                         socket.SOF_TIMESTAMPING_RX_HARDWARE |
                         socket.SOF_TIMESTAMPING_TX_HARDWARE |
                         socket.SOF_TIMESTAMPING_RAW_HARDWARE |
                         socket.SOF_TIMESTAMPING_RX_SOFTWARE |
                         socket.SOF_TIMESTAMPING_SOFTWARE)
    rsock.bind((cfg.if_name,0))
    CLIPOLL.register(rsock, select.POLLIN)

    tpipe = TCPTailPipe()
    tpipe.listen(cfg.anchor_addr, cfg.anchor_port)
    CLIPOLL.register(tpipe.sock, select.POLLIN)

    if cfg.server_host is not None:
        upipe = UDPTailPipe()
        upipe.bind(cfg.anchor_addr, cfg.anchor_port)
        upipe.connect(cfg.server_host, cfg.server_port)
        accept_client(upipe)

    while True:
        for (fd,flags) in CLIPOLL.poll(1000):
            try:
                if fd == rsock.fileno():
                    if flags & select.POLLIN:
                        recv_blink(rsock)
                    if flags & select.POLLERR:
                        recv_times(rsock)
                elif fd in CLIENTS:
                    if flags & select.POLLIN:
                        recv_client_msg(CLIENTS[fd],rsock)
                elif fd == tpipe.sock.fileno():
                    if flags & select.POLLIN:
                        accept_client(tpipe.accept())

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

    dprint(1, f'Tail Anchor <{cfg.if_eui64}> daemon starting...')

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

