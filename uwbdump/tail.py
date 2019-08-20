#!/usr/bin/python3
#
# tail.py	Tail python library
#

import sys
import time
import math
import ctypes
import struct
import socket
import netifaces

from ctypes import *


##
## Simple debugging print
##

class pr():
    
    DEBUG = 0

    def error(*args, **kwargs):
        print(time.strftime('%Y/%m/%d %H:%M:%S'), *args, file=sys.stderr, **kwargs)

    def debug(*args, **kwargs):
        if pr.DEBUG > 0:
            print(*args, file=sys.stderr, flush=True, **kwargs)


##
## DW1000 attributes
##

DW1000_SYSFS = '/sys/devices/platform/soc/3f204000.spi/spi_master/spi0/spi0.0/dw1000/'

def SetDWAttr(attr, data):
    with open(DW1000_SYSFS + attr, 'w') as f:
        f.write(str(data))

def GetDWAttr(attr):
    with open(DW1000_SYSFS + attr, 'r') as f:
        value = f.read()
    return value.rstrip()


##
## Kernel interface data structures
##

class Timespec(Structure):

    _fields_ = [("tv_sec", c_long),
                ("tv_nsec", c_long)]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)

    def __int__(self):
        return (self.tv_sec * 1000000000 + self.tv_nsec) << 32

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
        ("temp", c_int16),
        ("volt", c_int16),
    ]

    def __iter__(self):
        return ((x[0], getattr(self,x[0])) for x in self._fields_)

    def __str__(self):
        ret  = 'TimestampInfo'
        for (a,b) in self:
            ret += '\n  {}: {}'.format(a,str(b).replace('\n','\n  '))
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
        ret = 'Timestamp:'
        for (a,b) in self:
            ret += '\n  {}: {}'.format(a,str(b).replace('\n','\n  '))
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

    def match_bc(addr):
        return (addr == 2 * b'\xff') or (addr == 8 * b'\xff')
    
    def match_bcif(addr):
        return WPANFrame.match_if(addr) or WPANFrame.match_bc(addr)

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
        if WPANFrame.match_bcif(self.dst_addr) and WPANFrame.is_eui(self.src_addr):
            return self.src_addr.hex()
        if WPANFrame.match_bcif(self.src_addr) and WPANFrame.is_eui(self.dst_addr):
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
        else:
            raise ValueError
            
    def set_src_panid(self,panid):
        self.src_panid = panid
            
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

    def decode_ancl(self,ancl):
        for cmsg_level, cmsg_type, cmsg_data in ancl:
            if (cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SO_TIMESTAMPING):
                pr.debug('cmsg level={} type={} size={}\n'.format(cmsg_level,cmsg_type,len(cmsg_data)))
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
        ret = 'WPAN Frame\n'
        if self.timestamp is not None:
            ret += '  {}\n'.format(str(self.timestamp).replace('\n','\n  '))
        ret += '  Length         : {:d}\n'.format(self.frame_len)
        ret += '  Control        : 0x{:04x}\n'.format(self.frame_control)
        ret += '    Type         : {}\n'.format(self.frame_type)
        ret += '    Version      : {}\n'.format(self.frame_version)
        ret += '    Security     : {}\n'.format(self.security)
        ret += '    Pending      : {}\n'.format(self.pending)
        ret += '    Ack.Req.     : {}\n'.format(self.ack_req)
        ret += '    Dst mode     : {}\n'.format(self.dst_mode)
        ret += '    Src mode     : {}\n'.format(self.src_mode)
        ret += '    PanID comp   : {}\n'.format(self.panid_comp)
        ret += '  SequenceNr     : {}\n'.format(self.frame_seqnum)
        ret += '  Src Addr       : {}\n'.format(self.src_addr.hex())
        ret += '  Src PanID      : {:04x}\n'.format(self.src_panid)
        ret += '  Dst Addr       : {}\n'.format(self.dst_addr.hex())
        ret += '  Dst PanID      : {:04x}\n'.format(self.dst_panid)
        return ret
           


##
## Tail data format
##

def int8(x):
    if x > 127:
        x -= 256
    return x

def int16(x):
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
        self.tail_frmtype   = None
        self.tail_subtype   = None
        self.tail_txtime    = None
        self.tail_rxtimes   = None
        self.tail_cookie    = None
        self.tail_flags     = None
        self.tail_code      = None
        self.tail_test      = None
        self.tail_ies       = None
        self.tail_eies      = None
        self.tail_config    = {}
        
        if data is not None:
            self.decode(data)

        if ancl is not None:
            self.decode_ancl(ancl)
            
    def tsdecode(data):
        return struct.unpack_from('<Q', data.ljust(8, b'\0'))[0]
    
    def tsencode(data):
        return struct.pack('<Q', data)[0:4]

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
                    cookie = struct.unpack_from('16s',data,ptr)
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
                ## TBD
            elif self.tail_frmtype == 2:
                pass
                ## TBD
            elif self.tail_frmtype == 3:
                self.tail_owr = testbit(self.tail_subtype,3)
                self.tail_txtime = TailFrame.tsdecode(data[ptr:ptr+5])
                ptr += 5
                if not self.tail_owr:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    mask = 0
                    self.tail_rxtimes = {}
                    for i in range(0,cnt,8):
                        (val,) = struct.unpack_from('<B',data,ptr)
                        ptr += 1
                        mask |= val << i
                    for i in range(cnt):
                        if mask & 1:
                            (addr,) = struct.unpack_from('8s',data,ptr)
                            ptr += 8
                        else:
                            (addr,) = struct.unpack_from('2s',data,ptr)
                            ptr += 2
                        mask >>= 1
                        self.tail_rxtimes[byteswap(addr)] = TailFrame.tsdecode(data[ptr:ptr+5])
                        ptr += 5
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
                    for i in range(cnt):
                        (key,) = struct.unpack_from('<H',data,ptr)
                        ptr += 2
                        self.tail_config[key] = None
                elif self.tail_subtype == 3:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
                    for i in range(cnt):
                        (key,) = struct.unpack_from('<H',data,ptr)
                        ptr += 2
                        (val,) = struct.unpack_from('<p',data,ptr)
                        ptr += len(val) + 1
                        self.tail_config[key] = val
                elif self.tail_subtype == 4:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
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
                    for i in range(cnt):
                        (key,) = struct.unpack_from('<H',data,ptr)
                        ptr += 2
                        self.tail_config[key] = None
                elif self.tail_subtype == 2:
                    (cnt,) = struct.unpack_from('<B',data,ptr)
                    ptr += 1
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
                    raise NotImplementedError('encode IEs')
                if self.tail_eies is not None:
                    raise NotImplementedError('encode EIEs')
            elif self.tail_frmtype == 1:
                frame = makebits(self.tail_frmtype,4,4) | makebits(self.tail_subtype,0,4)
                flags = self.tail_flags
                data += struct.pack('<BB',frame, flags)
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
                    size = len(self.tail_rxtimes)
                    data += struct.pack('<B', size)
                    mask = 1
                    bits = 0
                    for addr in self.tail_rxtimes:
                        if len(addr) == 8:
                            bits |= mask
                        mask <<= 1
                    for i in range(0,size,8):
                        data += struct.pack('<B', (bits & 0xff))
                        bits >>= 8
                    for (addr,time) in self.tail_rxtimes:
                        data += struct.pack('s', byteswap(addr))
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
        if self.tail_protocol == 1:
            str += '  Tail Proto     : 0x37\n'
            if self.tail_frmtype == 0:
                str += '    Frame type   : Tag Blink {}:{}\n'.format(self.tail_frmtype,self.tail_subtype)
                str += '      EIEs       : {}\n'.format(self.tail_eies_present)
                str += '      IEs        : {}\n'.format(self.tail_ies_present)
                str += '      Cookie     : {}\n'.format(self.tail_cookie_present)
                str += '    Flags        : 0x{:02x}\n'.format(self.tail_flags)
                str += '      Listen     : {}\n'.format(self.tail_listen)
                str += '      Accel      : {}\n'.format(self.tail_accel)
                str += '      DCin       : {}\n'.format(self.tail_dcin)
                str += '      Salt       : {}\n'.format(self.tail_salt)
                if self.tail_cookie_present:
                    str += '    Cookie       : {}\n'.format(self.tail_cookie.hex())
                if self.tail_ies_present:
                    str += '    IEs          : {}\n'.format(len(self.tail_ies))
                    for (key,val) in self.tail_ies.items():
                        str += '      {:11s}: {}\n'.format(key,val)
            elif self.tail_frmtype == 1:
                str += '    Frame type   : Anchor Beacon {}:{}\n'.format(self.tail_frmtype,self.tail_subtype)
                str += '    Flags        : 0x{:02x}\n'.format(self.tail_flags)
            elif self.tail_frmtype == 2:
                str += '    Frame type   : Ranging Request {}:{}\n'.format(self.tail_frmtype,self.tail_subtype)
            elif self.tail_frmtype == 3:
                str += '    Frame type   : Ranging Response {}:{}\n'.format(self.tail_frmtype,self.tail_subtype)
                str += '      OWR        : {}\n'.format(self.tail_owr)
                str += '    TxTime       : {}\n'.format(self.tail_txtime)
                if not self.tail_owr:
                    str += '    RxTimes      : {}\n'.format(len(self.tail_rxtimes))
                    for (addr,time) in self.tail_rxtimes.items():
                        str += '      {}: {}\n'.format(addr.hex(),time)
            elif self.tail_frmtype == 4:
                str += '    Frame type   : Config Request {}:{}\n'.format(self.tail_frmtype,self.tail_subtype)
                if self_tail_subtype == 0:
                    str += '    Config Req   : RESET\n'
                    str += '      Magic      : {}\n'.format(self.tail_reset_magic)
                elif self_tail_subtype == 1:
                    str += '    Config Req   : ENUMERATE\n'
                    str += '      Iterator   : {}\n'.format(self.tail_iterator)
                elif self_tail_subtype == 2:
                    str += '    Config Req   : READ\n'
                    str += '      Keys       :\n'
                    for key in tail_config:
                        str += '        {}\n'.format(key)
                elif self_tail_subtype == 3:
                    str += '    Config Req   : WRITE\n'
                    str += '      Keys       :\n'
                    for (key,val) in tail_config.items():
                        str += '        {}   : {}\n'.format(key,val)
                elif self_tail_subtype == 4:
                    str += '    Config Req   : DELETE\n'
                    str += '      Keys       :\n'
                    for key in tail_config:
                        str += '        {}\n'.format(key)
                elif self_tail_subtype == 5:
                    str += '    Config Req   : SALT\n'
                    str += '      Salt       : {}'.format(self.tail_salt)
                elif self_tail_subtype == 15:
                    str += '    Config Req   : TEST\n'
                    str += '      Test       : {}'.format(self.tail_test)
            elif self.tail_frmtype == 5:
                str += '    Frame type   : Config Response {}:{}\n'.format(self.tail_frmtype,self.tail_subtype)
                if self_tail_subtype == 0:
                    str += '    Config Resp: RESET\n'
                    str += '      Magic      : {}\n'.format(self.tail_reset_magic)
                elif self_tail_subtype == 1:
                    str += '    Config Resp: ENUMERATE\n'
                    str += '      Iterator   : {}\n'.format(self.tail_iterator)
                    for key in tail_config:
                        str += '        {}\n'.format(key)
                elif self_tail_subtype == 2:
                    str += '    Config Resp: READ\n'
                    str += '      Keys       :\n'
                    for (key,val) in tail_config.items():
                        str += '        {}   : {}\n'.format(key,val)
                elif self_tail_subtype == 3:
                    str += '    Config Resp: WRITE\n'
                    str += '      Code       : {}\n'.format(self.tail_code)
                elif self_tail_subtype == 4:
                    str += '    Config Resp: DELETE\n'
                    str += '      Code       : {}\n'.format(self.tail_code)
                elif self_tail_subtype == 5:
                    str += '    Config Resp: SALT\n'
                    str += '      Salt       : {}'.format(self.tail_salt)
                elif self_tail_subtype == 15:
                    str += '    Config Resp: TEST\n'
                    str += '      Test       : {}'.format(self.tail_test)
        elif self.tail_protocol == 2:
            str += '  Tail Proto     : 0x38\n'
            str += '    Payload      : {}\n'.format(self.tail_payload.hex())
        elif self.tail_protocol == 0:
            str += '  Raw Payload    : {}\n'.format(self.tail_payload.hex())
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


