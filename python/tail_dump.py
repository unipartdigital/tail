#!/usr/bin/python3
#
# tail.py	Tail python library
#

import os
import sys
import time
import math
import ctypes
import struct
import socket
import netifaces
import traceback

from ctypes import *


##
## Simple error prints
##

def prints(*args, **kwargs):
    print(*args, end='', flush=True, **kwargs)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def eprints(*args, **kwargs):
    print(*args, file=sys.stderr, end='', flush=True, **kwargs)

def errhandler(msg,err):
    eprint('\n*** EXCEPTION {}:\n{}***\n'.format(msg,traceback.format_exc()))



##
## Network pipe for transferring json messages
##

class TailPipe:

    def __init__(self,sock=None):
        self.remote = None
        self.local = None
        self.sock = sock
        self.buff = b''
        
    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        self.buff = b''

    def clear(self):
        self.buff = b''

    def recv(self):
        data = self.sock.recv(4096)
        if len(data) < 1:
            raise ConnectionResetError
        return data

    def recvmsg(self):
        while not self.hasmsg():
            self.fillmsg()
        return self.getmsg()

    def fillmsg(self):
        self.buff += self.recv()

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

    def getsaddr(host,port,sock):
        addrs = socket.getaddrinfo(host, port)
        for addr in addrs:
            if addr[1] == sock:
                if addr[0] == socket.AF_INET6:
                    return addr[4]
        for addr in addrs:
            if addr[1] == sock:
                if addr[0] == socket.AF_INET:
                    return addr[4]
        return None


class TCPTailPipe(TailPipe):

    def __init__(self,sock=None):
        TailPipe.__init__(self,sock)
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
    def getsaddr(host,port):
        return TailPipe.getsaddr(host,port,socket.SOCK_STREAM)
    
    def connect(self, host, port):
        self.remote = TCPTailPipe.getsaddr(host,port)
        self.sock.connect(self.remote)

    def listen(self, addr, port):
        self.local = (addr,port)
        self.sock.bind(self.local)
        self.sock.listen()
    
    def accept(self):
        (csock,caddr) = self.sock.accept()
        pipe = TCPTailPipe(csock)
        pipe.local = self.local
        pipe.remote = caddr
        return pipe

        
class UDPTailPipe(TailPipe):

    def __init__(self,sock=None):
        TailPipe.__init__(self,sock)
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def getsaddr(host,port):
        return TailPipe.getsaddr(host,port,socket.SOCK_DGRAM)

    def connect(self,host,port):
        self.remote = UDPTailPipe.getsaddr(host,port)
        self.sock.connect(self.remote)

    def bind(self,addr,port):
        self.local = (addr,port)
        self.sock.bind(self.local)



##
## DW1000 attributes
##

DW1000_SYSFS = '/sys/devices/platform/soc/3f204000.spi/spi_master/spi0/spi0.0/dw1000/'

def SetDWAttr(attr, data):
    if os.path.isfile(DW1000_SYSFS + attr):
        with open(DW1000_SYSFS + attr, 'w') as f:
            f.write(str(data))

def GetDWAttr(attr):
    if os.path.isfile(DW1000_SYSFS + attr):
        with open(DW1000_SYSFS + attr, 'r') as f:
            value = f.read()
        return value.rstrip()
    return None


DW1000_SYSDT = '/sys/devices/platform/soc/3f204000.spi/spi_master/spi0/spi0.0/of_node/'

def GetDTAttrRaw(attr):
    if os.path.isfile(DW1000_SYSDT + attr):
        with open(DW1000_SYSDT + attr, 'rb') as f:
            data = f.read()
        return data
    return None

def GetDTAttrStr(attr):
    if os.path.isfile(DW1000_SYSDT + attr):
        with open(DW1000_SYSDT + attr, 'r') as f:
            data = f.read()
        return data.rstrip('\n\r\0')
    return None

def GetDTAttr(attr, form):
    if os.path.isfile(DW1000_SYSDT + attr):
        with open(DW1000_SYSDT + attr, 'rb') as f:
            data = f.read()
        return struct.unpack(form, data)
    return []


##
## Pretty printing key/value pairs
##

ATTR_KEY_LEN = 24

def fattr(key,val,ind=0,col=ATTR_KEY_LEN):
    return ind*' ' + key.ljust(col-ind) + ': ' + str(val).replace('\n', '\n'+ind*' ').replace(ind*' '+':',':')

def fattrnl(key,val,ind=0,col=ATTR_KEY_LEN):
    return fattr(key,val,ind,col) + '\n'

def fnlattr(key,val,ind=0,col=ATTR_KEY_LEN):
    return '\n' + fattr(key,val,ind,col)


##
## Kernel interface data structures
##

class Timespec(Structure):

    _fields_ = [("tv_sec", c_long),
                ("tv_nsec", c_long)]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)

    def __int__(self):
        return (self.tv_sec * 1000000000 + self.tv_nsec)

    def __float__(self):
        return float(int(self))

    def __str__(self):
        return '0x{:x}'.format(int(self))

    def __bool__(self):
        return bool(self.tv_sec or self.tv_nsec)

    def __dmp__(self, level):
        return [('Timespec', self.__str__, level)]


class Timehires(Structure):

    _fields_ = [
        ("tv_nsec", c_uint64),
        ("tv_frac", c_uint32),
        ("__res", c_uint32) ]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)

    def __int__(self):
        return ((self.tv_nsec << 32) | self.tv_frac)

    def __float__(self):
        return (float(self.tv_nsec) + self.tv_frac/4294967296)

    def __str__(self):
        return '0x{:x}.{:08x}'.format(self.tv_nsec,self.tv_frac)

    def __bool__(self):
        return bool(self.tv_nsec or self.tv_frac)

    def __dmp__(self,level):
        return [('Timehires', self.__str__, level)]


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
        ("temp", c_int16),
        ("volt", c_int16),
    ]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)

    def __str__(self):
        ret  = '[TimestampInfo]'
        for (key,val) in self:
            ret += fnlattr(key,val, 2)
        return ret

    def __dmp__(self,level):
        ret = [('TimestampInfo', '<struct>', level)]
        for (attr,val) in self:
            ret.append((attr,val,level+1))
        return ret


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

    def __str__(self):
        ret = '[Timestamp]'
        ret += fnlattr('sw', self.sw, 2)
        ret += fnlattr('hw', self.hw, 2)
        ret += fnlattr('hr', self.hires, 2)
        ret += fnlattr('ts', self.tsinfo, 2)
        return ret

    def __dmp__(self,level):
        ret = [('Timestamp', '<struct>', level)]
        for (attr,val) in self:
            if val:
                ret += val.__dmp__(level+1)
        return ret


##
## Support functions
##

def byteswap(data):
    return bytes(reversed(tuple(data)))

def bit(pos):
    return (1<<pos)

def testbit(data,pos):
    return bool(data & bit(pos))

def getbits(data,pos,cnt):
    return (data>>pos) & ((1<<cnt)-1)

def makebits(data,pos,cnt):
    return (data & ((1<<cnt)-1)) << pos



##
## 802.15.4 Frame Format
##

class WPANFrame:

    DSN = 0
    
    ADDR_NONE  = 0
    ADDR_SHORT = 2
    ADDR_EUI64 = 3

    if_addr    = None
    if_short   = None

    verbosity  = 0
    
    def __init__(self, data=None, ancl=None):
        self.timestamp      = None
        self.frame          = None
        self.frame_len      = 0
        self.frame_control  = None
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

        if data is not None:
            self.decode(data)
        if ancl is not None:
            self.decode_ancl(ancl)

    def set_ifaddr(if_addr=None, if_short=None):
        WPANFrame.if_addr  = if_addr
        WPANFrame.if_short = if_short

    def match_if(addr):
        return (addr == WPANFrame.if_addr) or (addr == WPANFrame.if_short)

    def match_bcast(addr):
        return (addr == 2 * b'\xff') or (addr == 8 * b'\xff')
    
    def match_local(addr):
        return WPANFrame.match_if(addr) or WPANFrame.match_bcast(addr)

    def is_eui(addr):
        return (type(addr) is bytes) and (len(addr) == 8) and (addr != 8 * b'\xff')
        
    def get_src_eui(self):
        if self.src_mode == WPANFrame.ADDR_EUI64:
            return self.src_addr.hex()
        return None
            
    def get_dst_eui(self):
        if self.dst_mode == WPANFrame.ADDR_EUI64:
            return self.dst_addr.hex()
        return None

    def get_peer_eui(self):
        if WPANFrame.match_local(self.dst_addr) and WPANFrame.is_eui(self.src_addr):
            return self.src_addr.hex()
        if WPANFrame.match_local(self.src_addr) and WPANFrame.is_eui(self.dst_addr):
            return self.dst_addr.hex()
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
        elif type(addr) is str:
            if len(addr) == 4:
                self.src_addr = bytes.fromhex(addr)
                self.src_mode = WPANFrame.ADDR_SHORT
            elif len(addr) == 16:
                self.src_addr = bytes.fromhex(addr)
                self.src_mode = WPANFrame.ADDR_EUI64
            else:
                raise ValueError
        else:
            raise ValueError
            
    def set_src_panid(self,panid):
        if type(panid) is int:
            self.src_panid = panid
        elif type(panid) is bytes and len(addr) == 2:
            self.src_panid = struct.pack('<H',panid)
        else:
            raise ValueError
            
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
        elif type(addr) is str:
            if len(addr) == 4:
                self.dst_addr = bytes.fromhex(addr)
                self.dst_mode = WPANFrame.ADDR_SHORT
            elif len(addr) == 16:
                self.dst_addr = bytes.fromhex(addr)
                self.dst_mode = WPANFrame.ADDR_EUI64
            else:
                raise ValueError
        else:
            raise ValueError
            
    def set_dst_panid(self,panid):
        if type(panid) is int:
            self.dst_panid = panid
        elif type(panid) is bytes and len(addr) == 2:
            self.dst_panid = struct.pack('<H',panid)
        else:
            raise ValueError

    def decode_ancl(self,ancl):
        for cmsg_level, cmsg_type, cmsg_data in ancl:
            #pr.debug('cmsg level={} type={} size={}\n'.format(cmsg_level,cmsg_type,len(cmsg_data)))
            if (cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SO_TIMESTAMPING):
                raw = cmsg_data.ljust(sizeof(Timestamp), b'\0')
                tss = Timestamp.from_buffer_copy(raw)
                self.timestamp = tss

    def decode(self,data):
        ptr = 0
        self.frame = data
        self.frame_len = len(data)
        (fc,sq) = struct.unpack_from('<HB',data,ptr)
        ptr += 3
        self.frame_control = fc
        self.frame_seqnum = sq
        self.frame_type = getbits(fc,0,3)
        self.frame_version = getbits(fc,12,2)
        self.security = testbit(fc,3)
        self.pending = testbit(fc,4)
        self.ack_req = testbit(fc,5)
        self.dst_mode = getbits(fc,10,2)
        self.src_mode = getbits(fc,14,2)
        self.panid_comp = testbit(fc,6)
        if self.dst_mode != 0:
            (panid,) = struct.unpack_from('<H',data,ptr)
            self.dst_panid = panid
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
                (panid,) = struct.unpack_from('<H',data,ptr)
                self.src_panid = panid
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
            raise NotImplementedError('decode WPAN security')
        self.header_len = ptr
        return ptr
            
    def encode(self):
        if self.frame_control is None:
            fc = self.frame_type & 0x07
            if self.security:
                fc |= bit(3)
            if self.pending:
                fc |= bit(4)
            if self.ack_req:
                fc |= bit(5)
            if self.panid_comp and (self.src_panid == self.dst_panid):
                fc |= bit(6)
            fc |= makebits(self.dst_mode,10,2)
            fc |= makebits(self.src_mode,14,2)
            fc |= makebits(self.frame_version,12,2)
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
            raise NotImplementedError('encode WPAN security')
        self.header_len = len(data)
        self.frame = data
        return data

    def __str__(self):
        if WPANFrame.verbosity == 0:
            ret = 'WPAN Frame'
            ret += ' size:{}'.format(self.frame_len)
            ret += ' src:{}'.format(self.src_addr.hex())
            ret += ' dst:{}'.format(self.dst_addr.hex())
        else:
            ret = 'WPAN Frame\n'
            if self.timestamp is not None:
                ret += fattrnl('Timestamp', self.timestamp, 2)
            ret += fattrnl('Length', self.frame_len, 2)
            ret += fattrnl('Control', '0x{:04x}'.format(self.frame_control), 2)
            ret += fattrnl('Type', self.frame_type, 4)
            ret += fattrnl('Version', self.frame_version, 4)
            ret += fattrnl('Security', self.security, 4)
            ret += fattrnl('Pending', self.pending, 4)
            ret += fattrnl('Ack.Req.', self.ack_req, 4)
            ret += fattrnl('Dst mode', self.dst_mode, 4)
            ret += fattrnl('Src mode', self.src_mode, 4)
            ret += fattrnl('PanID comp', self.panid_comp, 4)
            ret += fattrnl('SequenceNr', self.frame_seqnum, 2)
            ret += fattrnl('Src Addr', self.src_addr.hex(), 2)
            ret += fattrnl('Src PanID', '{:04x}'.format(self.src_panid), 2)
            ret += fattrnl('Dst Addr', self.dst_addr.hex(), 2)
            ret += fattrnl('Dst PanID', '{:04x}'.format(self.dst_panid), 2)
            
        return ret



##
## Tail data format
##

def int8(x):
    x = int(x) & 0xff
    if x > 127:
        x -= 256
    return x

def int16(x):
    x = int(x) & 0xffff
    if x > 32767:
        x -= 65536
    return x


class TailFrame(WPANFrame):

    PROTO_1 = 0x37
    PROTO_2 = 0x38

    IE_KEYS =  {
        0x00 : 'Batt',
        0x01 : 'Vreg',
        0x02 : 'Temp',
        0x40 : 'Vbatt',
        0x80 : 'Blinks',
        0xff : 'Debug',
    }

    IE_CONV =  {
        0x01 : lambda x: round(int8(x)/173+3.300, 3),
        0x02 : lambda x: round(int8(x)/1.14+23.0, 2),
        0x40 : lambda x: round(x*5/32768, 3),
    }

    def __init__(self, data=None, ancl=None, protocol=0):
        WPANFrame.__init__(self)
        self.tail_protocol  = protocol
        self.tail_payload   = None
        self.tail_listen    = False
        self.tail_accel     = False
        self.tail_dcin      = False
        self.tail_salt      = False
        self.tail_timing    = False
        self.tail_frmtype   = None
        self.tail_subtype   = None
        self.tail_txtime    = None
        self.tail_rxtime    = None
        self.tail_rxtimes   = None
        self.tail_rxinfo    = None
        self.tail_rxinfos   = None
        self.tail_cookie    = None
        self.tail_beacon    = None
        self.tail_flags     = None
        self.tail_code      = None
        self.tail_test      = None
        self.tail_ies       = None
        self.tail_eies      = None
        self.tail_config    = None
        
        if data is not None:
            self.decode(data)
        if ancl is not None:
            self.decode_ancl(ancl)
            
    def tsdecode(data):
        times = struct.unpack_from('<Q', data.ljust(8, b'\0'))[0]
        return times

    def tsencode(times):
        data = struct.pack('<Q',times)[0:5]
        return data

    def decode(self,data):
        ptr = WPANFrame.decode(self,data)
        (magic,) = struct.unpack_from('<B',data,ptr)
        ptr += 1
        if magic == TailFrame.PROTO_1:
            self.tail_protocol = 1
            (frame,) = struct.unpack_from('<B',data,ptr)
            ptr += 1
            self.tail_frmtype = getbits(frame,4,4)
            self.tail_subtype = getbits(frame,0,4)
            if self.tail_frmtype == 0:
                self.tail_eies_present   = testbit(frame,1)
                self.tail_ies_present    = testbit(frame,2)
                self.tail_cookie_present = testbit(frame,3)
                (flags,) = struct.unpack_from('<B',data,ptr)
                ptr += 1
                self.tail_flags  = flags
                self.tail_listen = testbit(flags,7)
                self.tail_accel  = testbit(flags,6)
                self.tail_dcin   = testbit(flags,5)
                self.tail_salt   = testbit(flags,4)
                if self.tail_cookie_present:
                    (cookie,) = struct.unpack_from('16s',data,ptr)
                    ptr += 16
                    self.tail_cookie = cookie
                if self.tail_ies_present:
                    (iec,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    self.tail_ies = {}
                    for i in range(iec):
                        (id,) = struct.unpack_from('<B',data,ptr)
                        ptr += 1
                        idf = getbits(id,6,2)
                        if idf == 0:
                            (val,) = struct.unpack_from('<B',data,ptr)
                            ptr += 1
                        elif idf == 1:
                            (val,) = struct.unpack_from('<H',data,ptr)
                            ptr += 2
                        elif idf == 2:
                            (val,) = struct.unpack_from('<I',data,ptr)
                            ptr += 4
                        else:
                            (val,) = struct.unpack_from('<p',data,ptr)
                            ptr += len(val) + 1
                        if id in TailFrame.IE_CONV:
                            val = TailFrame.IE_CONV[id](val)
                        if id in TailFrame.IE_KEYS:
                            self.tail_ies[TailFrame.IE_KEYS[id]] = val
                        else:
                            self.tail_ies['IE{:02X}'.format(id)] = val
                if self.tail_eies_present:
                    raise NotImplementedError('decode tail EIEs')
            elif self.tail_frmtype == 1:
                (flags,) = struct.unpack_from('<B',data,ptr)
                ptr += 1
                self.tail_flags = flags
                (id,) = struct.unpack_from('8s',data,ptr)
                self.tail_beacon = byteswap(id)
                ptr += 8
            elif self.tail_frmtype == 2:
                pass
                ## TBD
            elif self.tail_frmtype == 3:
                self.tail_owr = testbit(self.tail_subtype,3)
                (txtime,) = struct.unpack_from('5s',data,ptr)
                ptr += 5
                self.tail_txtime = TailFrame.tsdecode(txtime)
                if not self.tail_owr:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    bits = 0
                    self.tail_rxtimes = {}
                    for i in range(0,cnt,8):
                        (val,) = struct.unpack_from('<B',data,ptr)
                        ptr += 1
                        bits |= val << i
                    for i in range(cnt):
                        if testbit(bits,i):
                            (addr,) = struct.unpack_from('8s',data,ptr)
                            ptr += 8
                        else:
                            (addr,) = struct.unpack_from('2s',data,ptr)
                            ptr += 2
                        (rxdata,) = struct.unpack_from('5s',data,ptr)
                        ptr += 5
                        rxtime = TailFrame.tsdecode(rxdata)
                        self.tail_rxtimes[byteswap(addr)] = rxtime
                        if WPANFrame.match_if(byteswap(addr)):
                            self.tail_rxtime = rxtime
            elif self.tail_frmtype == 4:
                if self.tail_subtype == 0:
                    (magic,) = struct.unpack_from('<H',data,ptr)
                    ptr += 2
                    self.tail_reset_magic = magic
                elif self.tail_subtype == 1:
                    (iter,) = struct.unpack_from('<H',data,ptr)
                    ptr += 1
                    self.tail_iterator = iter
                elif self.tail_subtype == 2:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    self.tail_config = {}
                    for i in range(cnt):
                        (key,) = struct.unpack_from('<H',data,ptr)
                        ptr += 2
                        self.tail_config[key] = None
                elif self.tail_subtype == 3:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    self.tail_config = {}
                    for i in range(cnt):
                        (key,) = struct.unpack_from('<H',data,ptr)
                        ptr += 2
                        (val,) = struct.unpack_from('<p',data,ptr)
                        ptr += len(val) + 1
                        self.tail_config[key] = val
                elif self.tail_subtype == 4:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    self.tail_config = {}
                    for i in range(cnt):
                        (key,) = struct.unpack_from('<H',data,ptr)
                        ptr += 2
                        self.tail_config[key] = None
                elif self.tail_subtype == 5:
                    (salt,) = struct.unpack_from('<16s',data,ptr)
                    ptr += 16
                    self.tail_salt = salt
                elif self.tailubtype == 15:
                    (test,) = struct.unpack_from('<p',data,ptr)
                    ptr += len(test) + 1
                    self.tail_test = test
                else:
                    raise NotImplementedError('decode config request: {}'.format(self.tail_subtype))
            elif self.tail_frmtype == 5:
                if self.tail_subtype == 0:
                    (magic,) = struct.unpack_from('<H',data,ptr)
                    ptr += 2
                elif self.tail_subtype == 1:
                    (iter,cnt,) = struct.unpack_from('<HB',data,ptr)
                    ptr += 3
                    self.tail_iterator = iter
                    self.tail_config = {}
                    for i in range(cnt):
                        (key,) = struct.unpack_from('<H',data,ptr)
                        ptr += 2
                        self.tail_config[key] = None
                elif self.tail_subtype == 2:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    self.tail_config = {}
                    for i in range(cnt):
                        (key,val,) = struct.unpack_from('<Hs',data,ptr)
                        ptr += len(val) + 3
                        self.tail_config[key] = val
                elif self.tail_subtype == 3:
                    (code,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    self.tail_code = code
                elif self.tail_subtype == 4:
                    (code,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    self.tail_code = code
                elif self.tail_subtype == 5:
                    (salt,) = struct.unpack_from('<16s',data,ptr)
                    ptr += 16
                    self.tail_salt = salt
                elif self.tail_subtype == 15:
                    (test,) = struct.unpack_from('<p',data,ptr)
                    ptr += len(test) + 1
                    self.tail_test = test
                else:
                    raise NotImplementedError('decode config response: {}'.format(self.tail_subtype))
            elif self.tail_frmtype == 15:
                self.tail_timing = testbit(self.tail_subtype,3)
                txtime = testbit(self.tail_subtype,2)
                rxtime = testbit(self.tail_subtype,1)
                rxinfo = testbit(self.tail_subtype,0)
                if txtime:
                    (tstamp,) = struct.unpack_from('5s',data,ptr)
                    ptr += 5
                    self.tail_txtime = TailFrame.tsdecode(tstamp)
                if rxtime:
                    self.tail_rxtimes = {}
                if rxinfo:
                    self.tail_rxinfos = {}
                if rxtime or rxinfo:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    bits = 0
                    for i in range(0,cnt,8):
                        (val,) = struct.unpack_from('<B',data,ptr)
                        ptr += 1
                        bits |= val << i
                    for i in range(cnt):
                        if testbit(bits,i):
                            (addr,) = struct.unpack_from('8s',data,ptr)
                            ptr += 8
                        else:
                            (addr,) = struct.unpack_from('2s',data,ptr)
                            ptr += 2
                        if rxtime:
                            (val,) = struct.unpack_from('5s',data,ptr)
                            ptr += 5
                            tstamp = TailFrame.tsdecode(val)
                            self.tail_rxtimes[byteswap(addr)] = tstamp
                            if WPANFrame.match_if(byteswap(addr)):
                                self.tail_rxtime = tstamp
                        if rxinfo:
                            rxinfo = struct.unpack_from('<4H',data,ptr)
                            ptr += 8
                            self.tail_rxinfos[byteswap(addr)] = rxinfo
                            if WPANFrame.match_if(byteswap(addr)):
                                self.tail_rxinfo = rxinfo
            else:
                raise NotImplementedError('decode tail frametype: {}'.format(self.tail_frmtype))
    ## Tail encrypted protocol
        elif magic == TailFrame.PROTO_2:
            self.tail_protocol = 2
            self.tail_payload = data[ptr:]
    ## Tail protocols end
        else:
            self.tail_protocol = 0
            self.tail_payload = data[ptr-1:]
            
    def encode(self):
        data = WPANFrame.encode(self)
        if self.tail_protocol == 1:
            data += struct.pack('<B',TailFrame.PROTO_1)
            if self.tail_frmtype == 0:
                self.tail_subtype = 0
                if self.tail_cookie is not None:
                    self.tail_subtype |= bit(3)
                if self.tail_ies is not None:
                    self.tail_subtype |= bit(2)
                if self.tail_eies is not None:
                    self.tail_subtype |= bit(1)
                frame = makebits(self.tail_frmtype,4,4) | makebits(self.tail_subtype,0,4)
                data += struct.pack('<B',frame)
                self.tail_flags = 0
                if self.tail_listen:
                    self.tail_flags |= bit(7)
                if self.tail_accel:
                    self.tail_flags |= bit(6)
                if self.tail_dcin:
                    self.tail_flags |= bit(5)
                if self.tail_salt:
                    self.tail_flags |= bit(4)
                data += struct.pack('<B',self.tail_flags)
                if self.tail_cookie is not None:
                    data += struct.pack('16s',self.tail_cookie)
                if self.tail_ies is not None:
                    data += struct.pack('<B',len(self.tail_ies))
                    for (id,val) in self.tail_ies.items():
                        data += struct.pack('<B', id)
                        idf = getbits(id,6,2)
                        if idf == 0:
                            data += struct.pack('<B', val)
                        elif idf == 1:
                            data += struct.pack('<H', val)
                        elif idf == 2:
                            data += struct.pack('<I', val)
                        else:
                            data += struct.pack('<p', val)
                if self.tail_eies is not None:
                    raise NotImplementedError('encode EIEs')
            elif self.tail_frmtype == 1:
                frame = makebits(self.tail_frmtype,4,4) | makebits(self.tail_subtype,0,4)
                flags = self.tail_flags
                data += struct.pack('<BB', frame, flags)
                data += struct.pack('8s', byteswap(self.tail_beacon))
            elif self.tail_frmtype == 2:
                frame = makebits(self.tail_frmtype,4,4) | makebits(self.tail_subtype,0,4)
                flags = self.tail_flags
                data += struct.pack('<BB',frame, flags)
            elif self.tail_frmtype == 3:
                self.tail_subtype = 0
                if self.tail_owr:
                    self.tail_subtype |= bit(3)
                frame = makebits(self.tail_frmtype,4,4) | makebits(self.tail_subtype,0,4)
                data += struct.pack('<B',frame)
                data += TailFrame.tsencode(self.tail_txtime)
                if not self.tail_owr:
                    cnt = len(self.tail_rxtimes)
                    data += struct.pack('<B', cnt)
                    mask = 1
                    bits = 0
                    for addr in self.tail_rxtimes:
                        if len(addr) == 8:
                            bits |= mask
                        mask <<= 1
                    for i in range(0,cnt,8):
                        data += struct.pack('<B', ((bits>>i) & 0xff))
                    for (addr,time) in self.tail_rxtimes.items():
                        if len(addr) == 8:
                            data += struct.pack('8s', byteswap(addr))
                        else:
                            data += struct.pack('2s', byteswap(addr))
                        data += TailFrame.tsencode(time)
            elif self.tail_frmtype == 4:
                if self.tail_subtype == 0:
                    data += struct.pack('<H',self.tail_reset_magic)
                elif self.tail_subtype == 1:
                    data += struct.pack('<H',self.tail_iterator)
                elif self.tail_subtype == 2:
                    data += struct.pack('<B',len(self.tail_config))
                    for key in tail_config:
                        data += struct.pack('<H',key)
                elif self.tail_subtype == 3:
                    data += struct.pack('<B',len(self.tail_config))
                    for (key,val) in tail_config.items():
                        data += struct.pack('<Hp',key,val)
                elif self.tail_subtype == 4:
                    data += struct.pack('<B',len(self.tail_config))
                    for key in tail_config:
                        data += struct.pack('<H',key)
                elif self.tail_subtype == 5:
                    data += struct.pack('<16s',self.tail_salt)
                elif self.tail_subtype == 15:
                    data += struct.pack('<16s',self.tail_test)
                else:
                    raise NotImplementedError('encode config request {}'.format(self.tail_subtype))
            elif self.tail_frmtype == 5: 
                if self.tail_subtype == 0:
                    data += struct.pack('<H',self.tail_reset_magic)
                elif self.tail_subtype == 1:
                    data += struct.pack('<H',self.tail_iterator)
                    data += struct.pack('<B',len(self.tail_config))
                    for key in tail_config:
                        data += struct.pack('<H',key)
                elif self.tail_subtype == 2:
                    data += struct.pack('<B',len(self.tail_config))
                    for (key,val) in tail_config.items():
                        data += struct.pack('<Hp',key,val)
                elif self.tail_subtype == 3:
                    data += struct.pack('<B',self.tail_code)
                elif self.tail_subtype == 4:
                    data += struct.pack('<B',self.tail_code)
                elif self.tail_subtype == 5:
                    data += struct.pack('<16s',self.tail_salt)
                elif self.tail_subtype == 15:
                    data += struct.pack('<16s',self.tail_test)
                else:
                    raise NotImplementedError('encode config response {}'.format(self.tail_subtype))
            elif self.tail_frmtype == 15:
                self.tail_subtype = 0
                if self.tail_timing:
                    self.tail_subtype |= bit(3)
                if self.tail_txtime:
                    self.tail_subtype |= bit(2)
                if self.tail_rxtimes:
                    self.tail_subtype |= bit(1)
                if self.tail_rxinfos:
                    self.tail_subtype |= bit(0)
                frame = makebits(self.tail_frmtype,4,4) | makebits(self.tail_subtype,0,4)
                data += struct.pack('<B',frame)
                if self.tail_txtime:
                    data += TailFrame.tsencode(self.tail_txtime)
                if self.tail_rxtimes:
                    addrs = self.tail_rxtimes.keys()
                elif self.tail_rxinfos:
                    addrs = self.tail_rxinfos.keys()
                if self.tail_rxtimes or self.tail_rxinfos:
                    cnt = len(addrs)
                    data += struct.pack('<B', cnt)
                    mask = 1
                    bits = 0
                    for addr in addrs:
                        if len(addr) == 8:
                            bits |= mask
                        mask <<= 1
                    for i in range(0,cnt,8):
                        data += struct.pack('<B', ((bits>>i) & 0xff))
                    for addr in addrs:
                        if len(addr) == 8:
                            data += struct.pack('8s', byteswap(addr))
                        else:
                            data += struct.pack('2s', byteswap(addr))
                        if self.tail_rxtimes:
                            data += TailFrame.tsencode(self.tail_rxtimes[addr])
                        if self.tail_rxinfos:
                            data += struct.pack('<4H', *self.tail_rxinfos[addr])
            else:
                raise NotImplementedError('encode tail frametype {}'.format(self.tail_frmtype))
        elif self.tail_protocol == 2:
            data += struct.pack('<B',TailFrame.PROTO_2)
            data += self.tail_payload
        else:
            data += self.tail_payload
        self.frame_len = len(data)
        self.frame_data = data
        return data
        
    def __str__(self):
        str = WPANFrame.__str__(self)
        if WPANFrame.verbosity == 0:
            str += ' TAIL'
            if self.tail_protocol == 1:
                if self.tail_frmtype == 0:
                    str += ' Tag Blink sub:{} flags:{}'.format(self.tail_subtype, self.tail_flags)
                elif self.tail_frmtype == 1:
                    str += ' Anchor Beacon sub:{} flags:{} ref:{}'.format(self.tail_subtype, self.tail_flags, self.tail_beacon.hex())
                elif self.tail_frmtype == 2:
                    str += ' Ranging Request'
                elif self.tail_frmtype == 3:
                    str += ' Ranging Response OWR:{}'.format(self.tail_owr)
                    if self.tail_rxtimes:
                        str += ' rxtimes:{}'.format(len(self.tail_rxtimes))
                elif self.tail_frmtype == 4:
                    str += ' Config Request'
                elif self.tail_frmtype == 5:
                    str += ' Config Response'
            elif self.tail_protocol == 2:
                str += ' Encrypted Frame'
        else:
            if self.tail_protocol == 1:
                str += fattrnl('TAIL Proto', '0x37',2)
                if self.tail_frmtype == 0:
                    str += fattrnl('Frame type', 'Tag Blink {}:{}'.format(self.tail_frmtype,self.tail_subtype), 4)
                    str += fattrnl('EIEs', testbit(self.tail_subtype,1), 4)
                    str += fattrnl('IEs', testbit(self.tail_subtype,2), 4)
                    str += fattrnl('Cookie', testbit(self.tail_subtype,3), 4)
                    str += fattrnl('Flags', '0x{:02x}'.format(self.tail_flags), 4)
                    str += fattrnl('Listen', testbit(self.tail_flags,7), 6)
                    str += fattrnl('Accel', testbit(self.tail_flags,6), 6)
                    str += fattrnl('DCin', testbit(self.tail_flags,5), 6)
                    str += fattrnl('Salt', testbit(self.tail_flags,4), 6)
                    if self.tail_cookie is not None:
                        str += fattrnl('Cookie', self.tail_cookie.hex(), 4)
                    if self.tail_ies is not None:
                        str += fattrnl('IEs', len(self.tail_ies), 4)
                        for (key,val) in self.tail_ies.items():
                            str += fattrnl(key,val,6)
                elif self.tail_frmtype == 1:
                    str += fattrnl('Frame type', 'Anchor Beacon {}:{}'.format(self.tail_frmtype,self.tail_subtype), 4)
                    str += fattrnl('Flags', '0x{:02x}'.format(self.tail_flags), 4)
                    str += fattrnl('Ref', self.tail_beacon.hex(), 4)
                elif self.tail_frmtype == 2:
                    str += fattrnl('Frame type', 'Ranging Request {}:{}'.format(self.tail_frmtype,self.tail_subtype), 4)
                elif self.tail_frmtype == 3:
                    str += fattrnl('Frame type', 'Ranging Response {}'.format(self.tail_frmtype), 4)
                    str += fattrnl('OWR', self.tail_owr, 6)
                    str += fattrnl('TxTime', self.tail_txtime, 4)
                    if self.tail_rxtimes:
                        str += fattrnl('RxTimes', len(self.tail_rxtimes), 4)
                        for (addr,time) in self.tail_rxtimes.items():
                            str += fattrnl(addr.hex(),time,6)
                elif self.tail_frmtype == 4:
                    str += fattrnl('Frame type', 'Config Request {}:{}\n'.format(self.tail_frmtype,self.tail_subtype), 4)
                    if self_tail_subtype == 0:
                        str += fattrnl('Config Req', 'RESET', 4)
                        str += fattrnl('Magic', self.tail_reset_magic, 6)
                    elif self_tail_subtype == 1:
                        str += fattrnl('Config Req', 'ENUMERATE', 4)
                        str += fattrnl('Iterator', self.tail_iterator, 6)
                    elif self_tail_subtype == 2:
                        str += fattrnl('Config Req', 'READ', 4)
                        str += fattrnl('Keys', '', 6)
                        for key in tail_config:
                            str += fattrnl(key,'',8)
                    elif self_tail_subtype == 3:
                        str += fattrnl('Config Req', 'WRITE', 4)
                        str += fattrnl('Keys', '', 6)
                        for (key,val) in tail_config.items():
                            str += fattrnl(key,val,8)
                    elif self_tail_subtype == 4:
                        str += fattrnl('Config Req', 'DELETE', 4)
                        str += fattrnl('Keys', '', 6)
                        for key in tail_config:
                            str += fattrnl(key,'',8)
                    elif self_tail_subtype == 5:
                        str += fattrnl('Config Req', 'SALT', 4)
                        str += fattrnl('Salt', self.tail_salt, 6)
                    elif self_tail_subtype == 15:
                        str += fattrnl('Config Req', 'TEST', 4)
                        str += fattrnl('Test', self.tail_test, 6)
                elif self.tail_frmtype == 5:
                    str += fattrnl('Frame type', 'Config Response {}:{}'.format(self.tail_frmtype,self.tail_subtype), 4)
                    if self_tail_subtype == 0:
                        str += fattrnl('Config Resp', 'RESET', 4)
                        str += fattrnl('Magic', self.tail_reset_magic, 6)
                    elif self_tail_subtype == 1:
                        str += fattrnl('Config Resp', 'ENUMERATE', 4)
                        str += fattrnl('Iterator', self.tail_iterator, 6)
                        for key in tail_config:
                            str += fattrnl(key,'',8)
                    elif self_tail_subtype == 2:
                        str += fattrnl('Config Resp', 'READ', 4)
                        str += fattrnl('Keys', '', 6)
                        for (key,val) in tail_config.items():
                            str += fattrnl(key,val,8)
                    elif self_tail_subtype == 3:
                        str += fattrnl('Config Resp', 'WRITE', 4)
                        str += fattrnl('Code', self.tail_code, 6)
                    elif self_tail_subtype == 4:
                        str += fattrnl('Config Resp', 'DELETE', 4)
                        str += fattrnl('Code', self.tail_code, 6)
                    elif self_tail_subtype == 5:
                        str += fattrnl('Config Resp', 'SALT', 4)
                        str += fattrnl('Salt', self.tail_salt, 6)
                    elif self_tail_subtype == 15:
                        str += fattrnl('Config Resp', 'TEST', 4)
                        str += fattrnl('Test', self.tail_test, 6)
                elif self.tail_frmtype == 15:
                    str += fattrnl('Frame type', 'Ranging Resp#2 {}'.format(self.tail_frmtype), 4)
                    str += fattrnl('Timing', bool(self.tail_timing), 6)
                    str += fattrnl('TxTime', bool(self.tail_txtime), 6)
                    str += fattrnl('RxTimes', bool(self.tail_rxtimes), 6)
                    str += fattrnl('RxInfos', bool(self.tail_rxinfos), 6)
                    if self.tail_txtime:
                        str += fattrnl('TxTime', self.tail_txtime, 4)
                    if self.tail_rxtimes:
                        str += fattrnl('RxTimes', len(self.tail_rxtimes), 4)
                        for (addr,time) in self.tail_rxtimes.items():
                            str += fattrnl(addr.hex(),time,6)
                    if self.tail_rxinfos is not None:
                        str += fattrnl('RxInfos', len(self.tail_rxinfos), 4)
                        for (addr,rxinfo) in self.tail_rxinfos.items():
                            str += fattrnl(addr.hex(),rxinfo,6)
            elif self.tail_protocol == 2:
                str += fattrnl('TAIL Proto', '0x38', 2)
                str += fattrnl('Payload', self.tail_payload.hex(), 4)
            elif self.tail_protocol == 0:
                str += fattrnl('Raw Payload', tail_payload.hex(), 2)
        return str

    
## Missing values in socket
    
for name,value in (
        ('PROTO_IEEE802154', 0xf600),
        ('SO_TIMESTAMPING', 37),
        ('SOF_TIMESTAMPING_TX_HARDWARE',  (1<<0)),
        ('SOF_TIMESTAMPING_TX_SOFTWARE',  (1<<1)),
        ('SOF_TIMESTAMPING_RX_HARDWARE',  (1<<2)),
        ('SOF_TIMESTAMPING_RX_SOFTWARE',  (1<<3)),
        ('SOF_TIMESTAMPING_SOFTWARE',     (1<<4)),
        ('SOF_TIMESTAMPING_SYS_HARDWARE', (1<<5)),
        ('SOF_TIMESTAMPING_RAW_HARDWARE', (1<<6))):
    if not hasattr(socket, name):
        setattr(socket, name, value)


