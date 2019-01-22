#!/usr/bin/python3
#
# Anchor daemon for Tail algorithm development
#

import sys
import socket
import select
import ctypes
import struct
import array
import argparse
import ipaddress
import netifaces
import json

from ctypes import *
from pprint import pprint


class Config():
    if_name       = 'lowpan0'
    if_addr       = None
    if_index      = 0
    anchor_ip     = None
    anchor_eui    = None
    blink_addr    = 'ff12::42'
    blink_port    = 61616
    blink_send    = None
    blink_bind    = None
    udp_port      = 61666
    udp_bind      = None
    tcp_port      = 61666
    tcp_bind      = None
    dw1000_sysfs  = '/sys/devices/platform/soc/3f204000.spi/spi_master/spi0/spi0.0/dw1000/'

cfg = Config()

clients = {}
responses = {}


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class Timespec(Structure):

    _fields_ = [("tv_sec", c_long),
                ("tv_nsec", c_long)]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)

    def __int__(self):
        return ((self.tv_sec * 1000000000 + self.tv_nsec) << 32)

    def __str__(self):
        return '%#x' % int(self)

    def __bool__(self):
        return bool(self.tv_sec or self.tv_nsec)


class Timehires(Structure):

    _fields_ = [
        ("tv_nsec", c_uint64),
        ("tv_frac", c_uint32),
        ("__res", c_uint32) ]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)

    def __int__(self):
        return ((self.tv_nsec << 32) | self.tv_frac)

    def __str__(self):
        return '%#x' % int(self)

    def __bool__(self):
        return bool(self.tv_nsec or self.tv_frac)


class TimestampInfo(Structure):

    _fields_ = [
        ("rawts", c_uint64),
        ("lqi", c_uint16),
        ("snr", c_uint16),
        ("fpr", c_uint16),
        ("noise", c_uint16),
        ("rxpacc", c_uint16),
        ("fp_index", c_uint16),
        ("fp_ampl1", c_uint16),
        ("fp_ampl2", c_uint16),
        ("fp_ampl3", c_uint16),
        ("cir_pwr", c_uint32),
        ("fp_pwr", c_uint32),
        ("ttcko", c_uint32),
        ("ttcki", c_uint32),
        ("temp", c_uint16),
        ("volt", c_uint16),
    ]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)


class Timestamp(Structure):

    _fields_ = [
        ("sw", Timespec),
        ("legacy", Timespec),
        ("hw", Timespec),
        ("hires", Timehires),
        ("tsinfo", TimestampInfo),
    ]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)


class TailPipe:
    
    def __init__(self, sock=None):
        self.buff = b''
        self.sock = sock

    def socket(family, type):
        return TailPipe(socket.socket(family,type))
    
    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
            self.addr = None

    def recv(self):
        data = self.sock.recv(4096)
        if len(data) < 1:
            raise BrokenPipeError
        return data

    def recvmsg(self):
        while not self.hasmsg():
            self.fillmsg()
        return self.getmsg()

    def fillmsg(self):
        try:
            self.buff += self.recv()
        except ConnectionResetError:
            raise BrokenPipeError
        except ConnectionRefusedError:
            #eprint('TailPipe recv: Connection Refused')
            pass
    
    def hasmsg(self):
        return (self.buff.find(31) > 0)

    def getmsg(self):
        eom = self.buff.find(31)
        if eom > 0:
            msg = self.buff[0:eom]
            self.buff = self.buff[eom+1:]
            return msg
        elif eom == 0:
            self.buff = self.buff[1:]
        return None

    def send(self,data):
        self.sock.send(data)

    def sendmsg(self,data):
        self.send(data + b'\x1f')


class UDPPipe(TailPipe):
    
    def connect(remote=None, local=None):
        pipe = UDPPipe.socket(socket.AF_INET,socket.SOCK_DGRAM)
        pipe.addr = remote
        if local is not None:
            pipe.sock.bind(local)
        if remote is not None:
            pipe.sock.connect(remote)
        return pipe


class TCPPipe(TailPipe):

    def connect(remote=None, local=None):
        pipe = TCPPipe.socket(socket.AF_INET,socket.SOCK_STREAM)
        pipe.addr = remote
        if remote is not None:
            pipe.sock.connect(remote)
        return pipe



def SetDWAttr(attr, data):
    try:
        fd = open(cfg.dw1000_sysfs + attr, 'w')
        fd.write(str(data))
        fd.close()
        ret = 0
    except:
        ret = -1
    return ret


def GetDWAttr(attr):
    try:
        fd = open(cfg.dw1000_sysfs + attr, 'r')
        val = fd.read().rstrip()
        fd.close()
    except:
        val = None
    return val


def GetTagEUI(addr):
    ip = ipaddress.ip_address(addr)
    if ip.is_link_local:
        tag = bytearray(ip.packed[8:])
        tag[0] ^= 0x02
        return tag.hex()
    else:
        return None


def GetAnclTs(ancl):
    tss = Timestamp()
    for cmsg_level, cmsg_type, cmsg_data in ancl:
        if (cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SO_TIMESTAMPING):
            raw = cmsg_data.ljust(sizeof(Timestamp), b'\0')
            tss = Timestamp.from_buffer_copy(raw)
    return tss


def RecvBlink(bsock):
    (data, ancl, flags, rem) = bsock.recvmsg(4096, 1024, 0)
    try:
        (bst,bid) = struct.unpack('!16sI', data)
        eui = bst.decode()
    except:
        eui = GetTagEUI(rem[0].partition('%')[0])
        bid = None
    if bid in responses:
        pid = responses.pop(bid)
        msg = struct.pack('!16sI', cfg.anchor_eui.encode(), pid)
        bsock.sendto(msg, cfg.blink_send)
    tss = GetAnclTs(ancl)
    func = 'blinkRecv'
    argv = {
        'anchor'  : cfg.anchor_eui,
        'bid'     : bid,
        'tag'     : eui,
        'tss'     : str(tss.hires),
        'tsi'     : dict(tss.tsinfo),
    }
    SendRPC(None,func,argv,0)


def RecvStamp(bsock):
    (data, ancl, _, _) = bsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
    try:
        (bst,bid) = struct.unpack('!16sI', data[28:])
        eui = bst.decode()
    except:
        eui = cfg.anchor_eui
        bid = None
    tss = GetAnclTs(ancl)
    func = 'blinkXmit'
    argv = {
        'anchor'  : cfg.anchor_eui,
        'bid'     : bid,
        'tag'     : eui,
        'tss'     : str(tss.hires),
        'tsi'     : dict(tss.tsinfo),
    }
    SendRPC(None,func,argv,0)


def RPCBlink(rpc,bsock):
    args = rpc['args']
    bid = args.get('bid', 0)
    msg = struct.pack('!16sI', cfg.anchor_eui.encode(), bid)
    bsock.sendto(msg, cfg.blink_send)


def RPCAutoBlink(rpc,bsock):
    args = rpc['args']
    recv = args['recv']
    xmit = args['xmit']
    responses[recv] = xmit


def RPCGetEUI(rpc,pipe):
    args = rpc['args']
    seqn = rpc['seqn']
    data = cfg.anchor_eui
    func = 'getEUI::ret'
    argv = { 'value': data }
    seqn = seqn
    SendRPC(pipe, func, argv, seqn)


def RPCGetAttr(rpc,pipe):
    args = rpc['args']
    seqn = rpc['seqn']
    data = GetDWAttr(args['attr'])
    func = 'getAttr::ret'
    argv = { 'attr': args['attr'], 'value': data }
    seqn = seqn
    SendRPC(pipe, func, argv, seqn)


def RPCSetAttr(rpc,pipe):
    args = rpc['args']
    seqn = rpc['seqn']
    retv = SetDWAttr(args['attr'], args['value'])
    data = GetDWAttr(args['attr'])
    func = 'setAttr::ret'
    argv = { 'attr': args['attr'], 'value': data }
    seqn = seqn
    SendRPC(pipe, func, argv, seqn)


def SendRPC(pipe, func, args, seqn):
    rpc = {
        'func'  : func,
        'args'  : args,
        'seqn'  : seqn,
    }
    data = json.dumps(rpc).encode()
    if pipe is not None:
        pipe.sendmsg(data)
    else:
        for cl in clients.values():
            cl.sendmsg(data)


def RecvRPC(pipe,bsock):
    data = pipe.getmsg()
    rpc = json.loads(data.decode())
    fun = rpc.get('func', 'none')
    if fun == 'blink':
        RPCBlink(rpc,bsock)
    elif fun == 'autoBlink':
        RPCAutoBlink(rpc,bsock)
    elif fun == 'setAttr':
        RPCSetAttr(rpc,pipe)
    elif fun == 'getAttr':
        RPCGetAttr(rpc,pipe)
    elif fun == 'getEUI':
        RPCGetEUI(rpc,pipe)


def RecvPipe(pipe,bsock):
    pipe.fillmsg()
    while pipe.hasmsg():
        RecvRPC(pipe,bsock)


def AddClient(pipe):
    fd = pipe.sock.fileno()
    clients[fd] = pipe
    
def DelClient(pipe):
    fd = pipe.sock.fileno()
    if fd in clients:
        del clients[fd]


def SocketLoop():
    
    bsock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    bsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    ireq = struct.pack('I', cfg.if_index)
    bsock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, ireq)
    
    addr = socket.inet_pton(socket.AF_INET6, cfg.blink_addr)
    mreq = struct.pack('16sI', addr, cfg.if_index)
    bsock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

    bsock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 0)
    bsock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 1)

    bsock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                     socket.SOF_TIMESTAMPING_RX_HARDWARE |
                     socket.SOF_TIMESTAMPING_TX_HARDWARE |
                     socket.SOF_TIMESTAMPING_RAW_HARDWARE)
    
    bsock.bind(cfg.blink_bind)
    
    tsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tsock.bind(cfg.tcp_bind)
    tsock.listen()

    pobj = select.poll()
    pobj.register(tsock, select.POLLIN)
    pobj.register(bsock, select.POLLIN)

    for cl in clients.values():
        pobj.register(cl.sock, select.POLLIN)
    
    while True:
        fds = pobj.poll()
        for (fd,flags) in fds:
            if fd == bsock.fileno():
                if flags & select.POLLERR:
                    RecvStamp(bsock)
                if flags & select.POLLIN:
                    RecvBlink(bsock)
            elif fd == tsock.fileno():
                (psock,paddr) = tsock.accept()
                pipe = TailPipe(psock)
                AddClient(pipe)
                pobj.register(pipe.sock, select.POLLIN)
            elif fd in clients:
                pipe = clients[fd]
                try:
                    RecvPipe(pipe,bsock)
                except BrokenPipeError:
                    pobj.unregister(pipe.sock)
                    DelClient(pipe)


def main():
    
    parser = argparse.ArgumentParser(description="Anchor daemon")
    
    parser.add_argument('-i', '--interface', type=str, default=cfg.if_name)
    parser.add_argument('-u', '--udp_port', type=int, default=cfg.udp_port)
    parser.add_argument('-t', '--tcp_port', type=int, default=cfg.tcp_port)
    parser.add_argument('server', type=str, nargs='*')
    
    args = parser.parse_args()

    cfg.if_name   = args.interface
    cfg.if_addr   = netifaces.ifaddresses(args.interface)
    cfg.if_index  = socket.if_nametoindex(args.interface)
    
    cfg.anchor_link  = cfg.if_addr.get(netifaces.AF_INET6)[0]['addr']
    cfg.anchor_eui   = cfg.if_addr.get(netifaces.AF_PACKET)[0]['addr'].replace(':', '')
    cfg.anchor_ip    = cfg.anchor_link.split('%')[0]

    cfg.blink_bind  = ('', cfg.blink_port, 0, cfg.if_index)
    cfg.blink_send  = (cfg.blink_addr, cfg.blink_port, 0, cfg.if_index)

    cfg.tcp_port  = args.tcp_port
    cfg.tcp_bind  = ('', cfg.tcp_port)

    cfg.udp_port  = args.udp_port
    cfg.udp_bind = ('',cfg.udp_port)
    
    for server in args.server:
        addr = socket.getaddrinfo(server, cfg.udp_port, socket.AF_INET)[0][4]
        pipe = UDPPipe.connect(local=cfg.udp_bind, remote=addr)
        AddClient(pipe)

    eprint('Anchor server starting...')
    
    SocketLoop()

    return


if __name__ == "__main__":

    for name,value in (
            ('SO_TIMESTAMPING', 37),
            ('SO_SELECT_ERR_QUEUE', 45),
	    ('SOF_TIMESTAMPING_TX_HARDWARE',  (1<<0)),
  	    ('SOF_TIMESTAMPING_TX_SOFTWARE',  (1<<1)),
            ('SOF_TIMESTAMPING_RX_HARDWARE',  (1<<2)),
            ('SOF_TIMESTAMPING_RX_SOFTWARE',  (1<<3)),
            ('SOF_TIMESTAMPING_SOFTWARE',     (1<<4)),
            ('SOF_TIMESTAMPING_SYS_HARDWARE', (1<<5)),
            ('SOF_TIMESTAMPING_RAW_HARDWARE', (1<<6)),
            ('SOF_TIMESTAMPING_OPT_ID',       (1<<7)),
            ('SOF_TIMESTAMPING_TX_SCHED',     (1<<8)),
            ('SOF_TIMESTAMPING_TX_ACK',       (1<<9)),
            ('SOF_TIMESTAMPING_OPT_CMSG',     (1<<10)),
            ('SOF_TIMESTAMPING_OPT_TSONLY',   (1<<11)),
            ('SOF_TIMESTAMPING_OPT_STATS',    (1<<12)),
            ('SOF_TIMESTAMPING_OPT_PKTINFO',  (1<<13)),
            ('SOF_TIMESTAMPING_OPT_TX_SWHW',  (1<<14))):
        if not hasattr(socket, name):
            setattr(socket, name, value)
    main()

