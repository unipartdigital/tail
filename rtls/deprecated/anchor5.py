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


##
## Configuration
##

class Config():
    
    dw1000_channel  = 3
    dw1000_pcode    = 12
    dw1000_prf      = 64
    dw1000_rate     = 850
    dw1000_txpsr    = 1024
    dw1000_power    = 0x91919191
    dw1000_smart    = 0
    dw1000_sysfs    = '/sys/devices/platform/soc/3f204000.spi/spi_master/spi0/spi0.0/dw1000/'
    
    if_name       = 'wpan0'
    if_bind       = None
    if_addr       = None
    if_eui64      = None
    if_index      = None
    
    udp_port      = 61666
    udp_bind      = None
    
    tcp_port      = 61666
    tcp_bind      = None
    
cfg = Config()

clients = {}
responses = {}


##
## Debugging
##

DEBUG = 0

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def dprint(*args, **kwargs):
    if DEBUG > 0:
        print(*args, file=sys.stderr, flush=True, **kwargs)


##
## Kernel interface data structures
##

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

    
def byteswap(data):
    return bytes(reversed(tuple(data)))


##
## 802.15.4 Frame encoder
##

class WPANFrame:

    DSN = 0
    
    ADDR_NONE  = 0
    ADDR_SHORT = 2
    ADDR_EUI64 = 3
    
    TAIL_MAGIC = 0x37
    
    def __init__(self, data=None):
        self.frame_len      = 0
        self.frame_control  = 0
        self.frame_type     = 1
        self.frame_version  = 1
        self.frame_seqnum   = None
        self.header_len     = 0
        self.security       = False
        self.pending        = False
        self.ack_req        = False
        self.panid_comp     = True
        
        self.dst_mode       = 0
        self.dst_addr       = None
        self.dst_panid      = 0xffff
        
        self.src_mode       = 0
        self.src_addr       = None
        self.src_panid      = 0xffff
        
        self.payload        = None
        self.payload_len    = 0
     
        if data is not None:
            self.decode(data)

    def get_src_eui(self):
        if self.src_mode == WPANFrame.ADDR_EUI64:
            return self.src_addr.hex()
        return None
            
    def set_src_addr(self,addr):
        if addr is None:
            self.src_mode = WPANFrame.ADDR_NONE
            self.src_addr = None
        elif type(addr) is int:
            self.src_mode = WPANFrame.ADDR_SHORT
            self.src_addr = struct.pack('<H',addr)
        elif type(addr) is bytes:
            if len(addr) == 2:
                self.src_addr = addr
                self.src_mode = WPANFrame.ADDR_SHORT
            elif len(addr) == 8:
                self.src_addr = addr
                self.src_mode = WPANFrame.ADDR_EUI64
            else:
                raise ValueError
        else:
            raise ValueError
            
    def set_src_panid(self,panid):
        self.src_panid = panid
            
    def get_dst_eui(self):
        if self.dst_mode == WPANFrame.ADDR_EUI64:
            return self.dst_addr.hex()
        return None

    def set_dst_addr(self,addr):
        if addr is None:
            self.dst_mode = WPANFrame.ADDR_NONE
            self.dst_addr = None
        elif type(addr) is int:
            self.dst_mode = WPANFrame.ADDR_SHORT
            self.dst_addr = struct.pack('<H',addr)
        elif type(addr) is bytes:
            if len(addr) == 2:
                self.dst_addr = addr
                self.dst_mode = WPANFrame.ADDR_SHORT
            elif len(addr) == 8:
                self.dst_addr = addr
                self.dst_mode = WPANFrame.ADDR_EUI64
            else:
                raise ValueError
        else:
            raise ValueError
            
    def set_dst_panid(self,panid):
        self.dst_panid = panid

    def dump(self, header="802.15.4 Frame:\n", indent="  "):
        msg  = header
        msg += indent + "Length    : {} bytes\n".format(self.frame_len)
        msg += indent + "Header    : {} bytes\n".format(self.header_len)
        msg += indent + "Payload   : {} bytes\n".format(self.payload_len)
        msg += indent + "Control   : 0x{:02x}\n".format(self.frame_control)
        msg += indent + "Type      : {}\n".format(self.frame_type)
        msg += indent + "Version   : {}\n".format(self.frame_version)
        msg += indent + "Security  : {}\n".format(self.security)
        msg += indent + "Pending   : {}\n".format(self.pending)
        msg += indent + "Ack.Req.  : {}\n".format(self.ack_req)
        msg += indent + "PanID comp: {}\n".format(self.panid_comp)
        msg += indent + "Seq.num.  : {}\n".format(self.frame_seqnum)
        msg += indent + "Dst.mode  : {}\n".format(self.dst_mode)
        msg += indent + "Dst.addr  : {}\n".format(self.dst_addr)
        msg += indent + "Dst.panid : {}\n".format(self.dst_panid)
        msg += indent + "Src.mode  : {}\n".format(self.src_mode)
        msg += indent + "Src.addr  : {}\n".format(self.src_addr)
        msg += indent + "Src.panid : {}\n".format(self.src_panid)
        return msg
            
    def decode(self,data):
        ptr = 0
        self.frame_len = len(data)
        (fc,sq) = struct.unpack_from('<HB',data,ptr)
        ptr += 3
        self.frame_seqnum = sq
        self.frame_control = fc
        self.frame_type = fc & 0x07
        self.frame_version = (fc >> 12) & 0x03
        self.security = bool(fc & (1<<3))
        self.pending = bool(fc & (1<<4))
        self.ack_req = bool(fc & (1<<5))
        self.dst_mode = (fc >> 10) & 0x03
        self.src_mode = (fc >> 14) & 0x03
        self.panid_comp = bool(fc & (1<<6))
        if self.dst_mode != 0:
            (self.dst_panid,) = struct.unpack_from('<H',data,ptr)
            ptr += 2
            if self.dst_mode == self.ADDR_SHORT:
                (addr,) = struct.unpack_from('2s',data,ptr)
                self.dst_addr = byteswap(addr)
                ptr += 2
            elif self.dst_mode == self.ADDR_EUI64:
                (addr,) = struct.unpack_from('8s',data,ptr)
                self.dst_addr = byteswap(addr)
                ptr += 8
        else:
            self.dst_panid = None
            self.dst_addr  = None
        if self.src_mode != 0:
            if self.panid_comp:
                self.src_panid = self.dst_panid
            else:
                (self.src_panid,) = struct.unpack_from('<H',data,ptr)
                ptr += 2
            if self.src_mode == self.ADDR_SHORT:
                (addr,) = struct.unpack_from('2s',data,ptr)
                self.src_addr = byteswap(addr)
                ptr += 2
            elif self.src_mode == self.ADDR_EUI64:
                (addr,) = struct.unpack_from('8s',data,ptr)
                self.src_addr = byteswap(addr)
                ptr += 8
        else:
            self.src_panid = None
            self.src_addr  = None
        if self.security:
            raise ValueError('frame security not supported')
        self.header_len = ptr
        self.payload = data[ptr:]
        self.payload_len = len(self.payload)

    def encode(self):
        fc = self.frame_type & 0x07
        if self.security:
            fc |= 1<<3
        if self.pending:
            fc |= 1<<4
        if self.ack_req:
            fc |= 1<<5
        if self.panid_comp and (self.src_panid == self.dst_panid):
            fc |= 1<<6
        fc |= (self.dst_mode & 0x03) << 10
        fc |= (self.src_mode & 0x03) << 14
        fc |= (self.frame_version & 0x03) << 12
        self.frame_control = fc
        if self.frame_seqnum is None:
            self.frame_seqnum = WPANFrame.DSN
            WPANFrame.DSN = (WPANFrame.DSN + 1) & 0xff
        data = struct.pack('<HB', self.frame_control, self.frame_seqnum)
        if self.dst_mode != 0:
            data += struct.pack('<H',self.dst_panid)
            if self.dst_mode == self.ADDR_SHORT:
                data += struct.pack('2s',byteswap(self.dst_addr))
            elif self.dst_mode == self.ADDR_EUI64:
                data += struct.pack('8s',byteswap(self.dst_addr))
        if self.src_mode != 0:
            if not (self.panid_comp and (self.src_panid == self.dst_panid)):
                data += struct.pack('<H', self.src_panid)
            if self.src_mode == self.ADDR_SHORT:
                data += struct.pack('2s', byteswap(self.src_addr))
            elif self.src_mode == self.ADDR_EUI64:
                data += struct.pack('8s', byteswap(self.src_addr))
        if self.security:
            raise ValueError('frame security not supported')
        self.header_len = len(data)
        data += self.payload
        self.payload_len = len(self.payload)
        self.frame_len = len(data)
        return data


##
## Client communication
##

class TailPipe:
    
    def __init__(self, sock=None):
        self.inet = None
        self.addr = None
        self.port = None
        self.sock = sock
        self.buff = b''

    def new(sockfamily,socktype):
        return TailPipe(socket.socket(sockfamily,socktype))
    
    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
            self.addr = None
            self.buff = b''

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
            eprint('TailPipe recv: Connection Refused')
            pass
    
    def hasmsg(self):
        return (self.buff.find(31) > 0)

    def getmsg(self):
        eom = self.buff.find(31)
        if eom > 0:
            msg = self.buff[0:eom]
            self.buff = self.buff[eom+1:]
            return msg.decode()
        elif eom == 0:
            self.buff = self.buff[1:]
        return None

    def send(self,data):
        self.sock.sendall(data)

    def sendmsg(self,data):
        self.send(data.encode() + b'\x1f')


class UDPPipe(TailPipe):
    
    def create(remote=None, local=None):
        pipe = UDPPipe.new(socket.AF_INET,socket.SOCK_DGRAM)
        pipe.addr = remote
        if local is not None:
            pipe.sock.bind(local)
        if remote is not None:
            pipe.sock.connect(remote)
        return pipe


class TCPPipe(TailPipe):

    def create(remote=None, local=None):
        pipe = TCPPipe.new(socket.AF_INET,socket.SOCK_STREAM)
        pipe.addr = remote
        if remote is not None:
            pipe.sock.connect(remote)
        return pipe

    def accept(self, socket):
        (csock,caddr) = socket.accept()
        self.sock = csock
        self.addr = caddr[0]
        self.port = caddr[1]


##
## Hardware functions
##

def SetDWAttr(attr, data):
    with open(cfg.dw1000_sysfs + attr, 'w') as f:
        f.write(str(data))

def GetDWAttr(attr):
    with open(cfg.dw1000_sysfs + attr, 'r') as f:
        value = f.read()
    return value.rstrip()


def GetAnclTs(ancl):
    tss = Timestamp()
    for cmsg_level, cmsg_type, cmsg_data in ancl:
        if (cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SO_TIMESTAMPING):
            raw = cmsg_data.ljust(sizeof(Timestamp), b'\0')
            tss = Timestamp.from_buffer_copy(raw)
    return tss


def SendBlink(bsock,data):
    frame = WPANFrame()
    frame.payload = data
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(0xffff)
    bsock.send(frame.encode())
    return


def RecvBlink(bsock):
    (data, ancl, flags, rem) = bsock.recvmsg(4096, 1024, 0)
    frame = WPANFrame(data)
    eui = frame.get_src_eui()
    if frame.payload_len >= 4:
        (bid,) = struct.unpack_from('!I', frame.payload, 0)
        if bid in responses:
            pid = responses.pop(bid)
            msg = struct.pack('!I', pid)
            SendBlink(bsock,msg)
    else:
        bid = 0
    tss = GetAnclTs(ancl)
    func = 'blinkRecv'
    argv = {
        'anchor'  : cfg.if_eui64,
        'bid'     : bid,
        'tag'     : eui,
        'tsw'     : str(tss.sw),
        'tss'     : str(tss.hires),
        'tsi'     : dict(tss.tsinfo),
    }
    SendRPC(None,func,argv,0)
    return
   

def RecvStamp(bsock):
    (data, ancl, _, _) = bsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
    frame = WPANFrame(data)
    eui = frame.get_dst_eui()
    if frame.payload_len >= 4:
        (bid,) = struct.unpack_from('!I', frame.payload, 0)
    else:
        bid = 0
    tss = GetAnclTs(ancl)
    func = 'blinkXmit'
    argv = {
        'anchor'  : cfg.if_eui64,
        'bid'     : bid,
        'tag'     : eui,
        'tsw'     : str(tss.sw),
        'tss'     : str(tss.hires),
        'tsi'     : dict(tss.tsinfo),
    }
    SendRPC(None,func,argv,0)
    return


def RPCBlink(rpc,bsock):
    args = rpc['args']
    bid = args.get('bid', 0)
    msg = struct.pack('!I', bid)
    SendBlink(bsock,msg)


def RPCAutoBlink(rpc,bsock):
    args = rpc['args']
    recv = args['recv']
    xmit = args['xmit']
    responses[recv] = xmit


def RPCGetEUI(rpc,pipe):
    args = rpc['args']
    seqn = rpc['seqn']
    data = cfg.if_eui64
    func = 'getEUI::ret'
    argv = { 'value': data }
    SendRPC(pipe, func, argv, seqn)


def RPCGetAttr(rpc,pipe):
    args = rpc['args']
    seqn = rpc['seqn']
    try:
        data = GetDWAttr(args['attr'])
    except OSError:
        data = None
    func = 'getAttr::ret'
    argv = { 'attr': args['attr'], 'value': data }
    SendRPC(pipe, func, argv, seqn)


def RPCSetAttr(rpc,pipe):
    args = rpc['args']
    seqn = rpc['seqn']
    try:
        retv = SetDWAttr(args['attr'], args['value'])
        data = GetDWAttr(args['attr'])
    except OSError:
        data = None
    func = 'setAttr::ret'
    argv = { 'attr': args['attr'], 'value': data }
    SendRPC(pipe, func, argv, seqn)


def SendRPC(pipe, func, args, seqn):
    rpc = {
        'func'  : func,
        'args'  : args,
        'seqn'  : seqn,
    }
    data = json.dumps(rpc)
    if pipe is not None:
        pipe.sendmsg(data)
    else:
        for pipe in clients.values():
            pipe.sendmsg(data)


def RecvRPC(pipe,bsock):
    data = pipe.getmsg()
    rpc = json.loads(data)
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
    pipe.close()


def SocketLoop():
    
    tsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tsock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    tsock.bind(cfg.tcp_bind)
    tsock.listen()

    bsock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.PROTO_IEEE802154)

    bsock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                     socket.SOF_TIMESTAMPING_RX_HARDWARE |
                     socket.SOF_TIMESTAMPING_TX_HARDWARE |
                     socket.SOF_TIMESTAMPING_RAW_HARDWARE |
                     socket.SOF_TIMESTAMPING_TX_SOFTWARE |
                     socket.SOF_TIMESTAMPING_RX_SOFTWARE |
                     socket.SOF_TIMESTAMPING_SOFTWARE)
    
    bsock.bind(cfg.if_bind)
    
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
                pipe = TCPPipe()
                pipe.accept(tsock)
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
    
    global DEBUG
    
    parser = argparse.ArgumentParser(description="Anchor daemon")
    
    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-i', '--interface', type=str, default=cfg.if_name)
    parser.add_argument('-u', '--udp_port', type=int, default=cfg.udp_port)
    parser.add_argument('-t', '--tcp_port', type=int, default=cfg.tcp_port)
    parser.add_argument('server', type=str, nargs='*')
    
    args = parser.parse_args()

    DEBUG = args.debug

    cfg.if_name  = args.interface
    cfg.if_bind  = (cfg.if_name, 0)
    
    addrs = netifaces.ifaddresses(cfg.if_name).get(netifaces.AF_PACKET)
    cfg.if_eui64 = addrs[0]['addr'].replace(':','')
    cfg.if_addr = bytes.fromhex(cfg.if_eui64)

    dprint('if_addr: {}'.format(cfg.if_addr))
    dprint('if_eui64: {}'.format(cfg.if_eui64))

    cfg.tcp_port = args.tcp_port
    cfg.tcp_bind = ('', cfg.tcp_port)
    
    cfg.udp_port = args.udp_port
    cfg.udp_bind = ('',cfg.udp_port)
    
    for server in args.server:
        addr = socket.getaddrinfo(server, cfg.udp_port, socket.AF_INET)[0][4]
        pipe = UDPPipe.create(local=cfg.udp_bind, remote=addr)
        AddClient(pipe)

    eprint('Anchor server starting...')
    
    try:
        SetDWAttr('channel', cfg.dw1000_channel)
        SetDWAttr('pcode', cfg.dw1000_pcode)
        SetDWAttr('prf', cfg.dw1000_prf)
        SetDWAttr('rate', cfg.dw1000_rate)
        SetDWAttr('txpsr', cfg.dw1000_txpsr)
        SetDWAttr('smart_power', cfg.dw1000_smart)
        SetDWAttr('tx_power', cfg.dw1000_power)

        SocketLoop()

    except KeyboardInterrupt:
        eprint('Exiting...')
    


for name,value in (
        ('PROTO_IEEE802154', 0xf600),
        ('SO_TIMESTAMPING', 37),
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

if __name__ == "__main__": main()

