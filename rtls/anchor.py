#!/usr/bin/python3
#
# Test hack for developing RPi Tail algorithms
#

import pprint
import argparse
import ipaddress
import netifaces
import socket
import select
import fcntl
import struct
import array
import ctypes
import json

from ctypes import *


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
    server_addr   = None
    server_port   = 61666
    server_bind   = None
    dw1000_sysfs  = '/sys/devices/platform/soc/3f204000.spi/spi_master/spi0/spi0.0/dw1000/'

cfg = Config()


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


class Timespec(Structure):

    _fields_ = [("tv_sec", c_long),
                ("tv_nsec", c_long)]

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

    def __int__(self):
        return ((self.tv_nsec << 32) | self.tv_frac)

    def __str__(self):
        return '%#x' % int(self)

    def __bool__(self):
        return bool(self.tv_nsec or self.tv_frac)


class Timestamp(Structure):

    _fields_ = [
        ("sw", Timespec),
        ("legacy", Timespec),
        ("hw", Timespec),
        ("hires", Timehires) ]


def SetDWAttr(attr, data):
    try:
        fd = open(cfg.dw1000_sysfs + attr, 'w')
        fd.write(str(data))
        fd.close()
        ret = 0
        #print('SetDWAttr({}, {})'.format(attr,data))
    except:
        print('SetDWAttr {} := {} failed'.format(attr,data))
        ret = -1
    return ret


def GetDWAttr(attr):
    try:
        fd = open(cfg.dw1000_sysfs + attr, 'r')
        val = fd.read()
        fd.close()
        #print('GetDWAttr({}) = {}'.format(attr,val))
    except:
        print('GetDWAttr {} failed'.format(attr))
        val = ''
    return val.rstrip()


def GetTagEUI(addr):
    ip = ipaddress.ip_address(addr)
    if ip.is_link_local:
        tag = bytearray(ip.packed[8:])
        tag[0] ^= 0x02
        return tag.hex()
    else:
        return '0'


def GetAnclTs(ancl):
    tss = Timestamp()
    for cmsg_level, cmsg_type, cmsg_data in ancl:
        if (cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SO_TIMESTAMPING):
            raw = cmsg_data.ljust(sizeof(Timestamp), b'\0')
            tss = Timestamp.from_buffer_copy(raw)
    return tss


def RecvBlink(bsock, rsock):
    (data, ancl, flags, rem) = bsock.recvmsg(4096, 1024, 0)
    try:
        (bst,bid) = struct.unpack('!16sI', data)
        eui = bst.decode()
    except:
        eui = GetTagEUI(rem[0].partition('%')[0])
        bid = None
    tss = GetAnclTs(ancl)
    msg = {
        'func'    : 'blinkRecv',
        'args'    : {
            'anchor'  : cfg.anchor_eui,
            'bid'     : bid,
            'tag'     : eui,
            'tss'     : str(tss.hires),
        },
        'seqn'    : 0,
    }
    #print('RECV BLINK:')
    #pprint.pprint(msg)
    SendRPC(rsock,msg)
    
    
def RecvStamp(bsock, rsock):
    (data, ancl, _, _) = bsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
    try:
        (bst,bid) = struct.unpack('!16sI', data[28:])
        eui = bst.decode()
    except:
        eui = cfg.anchor_eui
        bid = None
    tss = GetAnclTs(ancl)
    msg = {
        'func'    : 'blinkXmit',
        'args'    : {
            'anchor'  : cfg.anchor_eui,
            'bid'     : bid,
            'tag'     : eui,
            'tss'     : str(tss.hires),
        },
        'seqn'    : 0,
    }
    #print('XMIT BLINK:')
    #pprint.pprint(msg)
    SendRPC(rsock,msg)


def RPCBlink(rpc,sock):
    args = rpc['args']
    bid = args.get('bid', 0)
    msg = struct.pack('!16sI', cfg.anchor_eui.encode(), bid)
    sock.sendto(msg, cfg.blink_send)


def RPCGetEUI(rpc,rsock):
    args = rpc['args']
    eui = cfg.anchor_eui
    msg = {
        'func'  : 'getEUI::ret',
        'args'  : { 'value': eui },
        'seqn'  : rpc['seqn'],
    }
    SendRPC(rsock, msg)


def RPCGetAttr(rpc,rsock):
    args = rpc['args']
    val = GetDWAttr(args['attr'])
    msg = {
        'func'  : 'getAttr::ret',
        'args'  : { 'attr': args['attr'], 'value': val },
        'seqn'  : rpc['seqn'],
    }
    SendRPC(rsock, msg)
    

def RPCSetAttr(rpc,rsock):
    args = rpc['args']
    val = SetDWAttr(args['attr'], args['value'])
    msg = {
        'func'     : 'setAttr::ret',
        'args'     : { 'attr': args['attr'], 'value': val },
        'seqn'     : rpc['seqn'],
    }
    SendRPC(rsock, msg)


def SendRPC(sock, msg):
    res = json.dumps(msg)
    sock.sendto(res.encode(), cfg.server_send)

    
def RecvRPC(bsock, rsock):
    (data, remote) = rsock.recvfrom(4096)
    rpc = json.loads(data.decode())
    func = rpc.get('func', 'none')
    if func == 'blink':
        RPCBlink(rpc,bsock)
    elif func == 'setAttr':
        RPCSetAttr(rpc,rsock)
    elif func == 'getAttr':
        RPCGetAttr(rpc,rsock)
    elif func == 'getEUI':
        RPCGetEUI(rpc,rsock)
        

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
                     socket.SOF_TIMESTAMPING_RAW_HARDWARE )
    
    bsock.bind(cfg.blink_bind)
    
    rsock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rsock.bind(cfg.server_bind)

    pobj = select.poll()
    pobj.register(rsock, select.POLLIN)
    pobj.register(bsock, select.POLLIN)
    
    while True:
        fds = pobj.poll()
        for (fd,flags) in fds:
            if fd == bsock.fileno():
                if flags & select.POLLERR:
                    RecvStamp(bsock,rsock)
                if flags & select.POLLIN:
                    RecvBlink(bsock,rsock)
            elif fd == rsock.fileno():
                RecvRPC(bsock,rsock)


def main():
    global cfg
    
    parser = argparse.ArgumentParser(description="Anchor daemon")
    
    parser.add_argument('-i', '--interface', type=str, default=cfg.if_name,
                        help="Listening network interface")
    parser.add_argument('-p', '--port', type=int, default=cfg.server_port)
    parser.add_argument('-s', '--server', type=str)
    
    args = parser.parse_args()

    server = socket.getaddrinfo(args.server, args.port, socket.AF_INET6)[0][4]

    cfg.if_name   = args.interface
    cfg.if_addr   = netifaces.ifaddresses(args.interface)
    cfg.if_index  = socket.if_nametoindex(args.interface)
    
    cfg.anchor_eui   = cfg.if_addr.get(netifaces.AF_PACKET)[0]['addr'].replace(':', '')
    cfg.anchor_link  = cfg.if_addr.get(netifaces.AF_INET6)[0]['addr']
    cfg.anchor_ip    = cfg.anchor_link.split('%')[0]

    cfg.blink_bind  = ('', cfg.blink_port, 0, cfg.if_index)
    cfg.blink_send  = (cfg.blink_addr, cfg.blink_port, 0, cfg.if_index)

    cfg.server_addr = server[0]
    cfg.server_port = server[1]
    cfg.server_send = server
    cfg.server_bind = ('', server[1])

    print('Anchor server starting...')
    
    SocketLoop()
    


if __name__ == "__main__":
    main()

