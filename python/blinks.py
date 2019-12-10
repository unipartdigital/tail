#!/usr/bin/python3
#
# Helper functions/classes/code for Tail
#

import sys
import math
import time
import json
import socket
import select
import threading
import traceback

import numpy as np

from tail import *
from dwarf import *


class Timer:

    SLEEP_MIN = 500E-6   # 500us
    
    def __init__(self):
        self.start = time.time()
        self.timer = self.start

    def get(self):
        return self.timer - self.start
    
    def nap(self,delay):
        self.timer += delay
        while True:
            sleep = self.timer - time.time()
            if sleep < Timer.SLEEP_MIN:
                break
            time.sleep(sleep/2)
        return self.get()

    def sync(self,delay=0.0):
        self.nap(delay)
        self.timer = time.time()
        return self.get()


class DW1000:

    DEV_ATTRS = (
        'channel',
        'prf',
        'pcode',
        'txpsr',
        'rate',
        'smart_power',
        'tx_power',
        'xtalt',
        'antd',
        'profile',
        'snr_threshold',
        'fpr_threshold',
        'noise_threshold',
    )
    
    PRINT_ATTRS = (
        'channel',
        'prf',
        'pcode',
        'txpsr',
        'rate',
        'smart_power',
        'tx_power',
        'xtalt',
        'antd',
    )

    def __init__(self, rpc, name, host, port=None, coord=None):
        self.rpc = rpc
        self.pipe = None
        self.name = name
        self.host = host
        self.port = port
        self.coord = coord

    def load_config(self, **kwargs):
        for (attr,value) in kwargs.items():
            try:
                getattr(self,attr)
                setattr(self,attr,value)
            except AttributeError:
                eprint(f'DW1000: Invalid config option: {attr} := {value}')

    @classmethod
    def from_config(cls, rpc, **kwargs):
        dev = cls(rpc)
        dev.load_config(kwargs)
    
    def connect(self):
        self.pipe = TCPTailPipe()
        self.pipe.connect(self.host,self.port)
        self.rpc.add_device(self)
        self.eui = self.get_eui()
        self.register_udp_bcast()

    def disconnect(self):
        self.rpc.del_device(self)
        self.pipe.close()
        self.pipe = None

    def sendmsg(self,msg):
        self.pipe.sendmsg(msg)

    def sendudp(self,msg):
        self.rpc.sendudpmsgto(msg,self.pipe.remote)

    def sendargs(self,**kwargs):
        msg = json.dumps(kwargs)
        self.sendmsg(msg)

    def sendargsudp(self,**kwargs):
        msg = json.dumps(kwargs)
        self.sendudp(msg)

    def register_udp_bcast(self):
        self.sendargs(Type='UDP', Port=self.rpc.uport)

    def unregister_udp_bcast(self):
        self.sendargs(Type='NOUDP')

    def get_eui(self):
        args = self.rpc.call(self, Func='GETEUI')
        return args.get('Value',None)

    def get_dt_attr(self,attr,form):
        args = self.rpc.call(self, Func='GETDTATTR', Attr=attr, Format=form)
        return args.get('Value',None)

    def get_dw1000_attr(self,attr):
        args = self.rpc.call(self, Func='GETDWATTR', Attr=attr)
        return args.get('Value',None)

    def set_dw1000_attr(self,attr,val):
        if attr in self.CONV_ATTR:
            val = self.CONV_ATTR[attr](val)
        args = self.rpc.call(self, Func='SETDWATTR', Attr=attr, Value=val)
        return args.get('Value',None)

    def print_dw1000_attrs(self):
        eprint('{} <{}>'.format(self.name,self.eui))
        for attr in DW1000.PRINT_ATTRS:
            val = self.get_dw1000_attr(attr)
            eprint('  {:20s}: {}'.format(attr,val))

    def distance_to(self,rem):
        D = self.coord - rem.coord
        return np.sqrt(np.dot(D,D.T))


    ##
    ## Static members
    ##

    def print_all_remote_attrs(remotes,summary=False):
        if summary:
            eprints(' {:24s}'.format('HOSTS'))
            for rem in remotes:
                eprints(' {:10s}'.format(rem.name[:9]))
            for attr in DW1000.PRINT_ATTRS:
                eprints('\n  {:20s}:  '.format(attr))
                for rem in remotes:
                    value = rem.get_dw1000_attr(attr)
                    eprints(' {:10s}'.format(str(value)))
            eprint()
        else:
            for rem in remotes:
                eprint('{} <{}>'.format(rem.name,rem.eui))
                for attr in DW1000.PRINT_ATTRS:
                    value = rem.get_dw1000_attr(attr)
                    eprint('  {:20s}: {}'.format(attr,value))

    def add_print_arguments(parser):
        parser.add_argument('--print-eui', action='store_true', default=False, help='Print EUI64 value')
        for attr in DW1000.PRINT_ATTRS:
            parser.add_argument('--print-'+attr, action='store_true', default=False, help='Print attribute <{}> value'.format(attr))

    def handle_print_arguments(args,remotes):
        ret = False
        for rem in remotes:
            if getattr(args, 'print_eui'):
                print(rem.eui)
            for attr in DW1000.PRINT_ATTRS:
                if getattr(args, 'print_'+attr):
                    val = rem.get_dw1000_attr(attr)
                    ret = True
                    print(val)
        return ret
    
    def add_device_arguments(parser):
        for attr in DW1000.DEV_ATTRS:
            parser.add_argument('--' + attr, type=str, default=None)

    def handle_device_arguments(args,remotes):
        for attr in DW1000.DEV_ATTRS:
            val = getattr(args,attr)
            if val is not None:
                for rem in remotes:
                    rem.set_dw1000_attr(attr, val)

    ##
    ## Attribute conversions
    ##
    
    def tx_power_code_to_list(code):
        if isinstance(code,str):
            code = int(code,0)
        C = (code >> 5) & 0x07
        F = (code >> 0) & 0x1f
        c = (6 - C) * 3.0
        f = F * 0.5
        return [ c, f ]

    def tx_power_list_to_code(lst):
        c = int(lst[0] / 3)
        d = int(lst[1] * 2)
        if c<0 or c>6:
            raise ValueError
        if d<0 or d>31:
            raise ValueError
        return (((6 - c) << 5) | d)

    def tx_power_string_to_code(txpwr):
        T = txpwr.split('+')
        n = len(T)
        if n == 2:
            a = float(T[0])
            b = float(T[1])
            c = int(a / 3)
            d = int(b * 2)
            if c<0 or c>6:
                raise ValueError
            if a != 3*c:
                raise ValueError
            if d<0 or d>31:
                raise ValueError
            if b != d/2:
                raise ValueError
            return (((6 - c) << 5) | d)
        elif n == 1:
            a = int(txpwr,0)
            return a
        else:
            raise ValueError

    def tx_power_reg_to_list(reg):
        if isinstance(reg,str):
            reg = int(reg,0)
        return DW1000.tx_power_code_to_list(reg >> 16)

    def tx_power_to_reg(txpwr):
        if isinstance(txpwr,int):
            return txpwr
        
        elif isinstance(txpwr,float):
            return int(txpwr) ## convert to a+b?
            
        elif isinstance(txpwr,str):
            T = txpwr.split(':')
            n = len(T)
            if n == 4:
                A = DW1000.tx_power_string_to_code(T[0])
                B = DW1000.tx_power_string_to_code(T[1])
                C = DW1000.tx_power_string_to_code(T[2])
                D = DW1000.tx_power_string_to_code(T[3])
                if A<0 or B<0 or C<0 or D<0:
                    raise ValueError
                if A>255 or B>255 or C>255 or D>255:
                    raise ValueError
                return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,B,C,D)
            elif n == 2:
                A = DW1000.tx_power_string_to_code(T[0])
                B = DW1000.tx_power_string_to_code(T[1])
                if A<0 or B<0:
                    raise ValueError
                if A>255 or B>255:
                    raise ValueError
                return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,A,B,B)
            elif n == 1:
                A = DW1000.tx_power_string_to_code(T[0])
                if A<0:
                    raise ValueError
                if A<256:
                    return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,A,A,A)
                else:
                    return '0x{:08x}'.format(A)
        raise ValueError

    def validate_txpsr(psr):
        psr = int(psr)
        if psr in (64,128,256,512,1024,2048,4096):
            return psr
        raise ValueError(f'Invalid PSR {psr}')
    
    def validate_rate(rate):
        rate = int(rate)
        if rate in (110,850,6800):
            return rate
        raise ValueError(f'Invalid rate {rate}')

    def validate_prf(prf):
        prf = int(prf)
        if prf in (16,64):
            return prf
        raise ValueError(f'Invalid PRF {prf}')

    def validate_channel(ch):
        ch = int(ch)
        if ch in (1,2,3,4,5,7):
            return ch
        raise ValueError(f'Invalid Channel {ch}')
    
    CONV_ATTR = {
        'channel'   : validate_channel,
        'prf'       : validate_prf,
        'rate'      : validate_rate,
        'txpsr'     : validate_txpsr,
        'tx_power'  : tx_power_to_reg,
    }


class RPC:

    def __init__(self, udp_port=9813):
        self.running = False
        self.seqnum = 1
        self.pipes = {}
        self.calls = {}
        self.handler = {}
        self.socks = select.poll()
        self.uport = udp_port
        self.upipe = UDPTailPipe()
        self.upipe.bind('', udp_port)
        self.ufile = self.upipe.fileno()
        self.pipes[self.ufile] = self.upipe
        self.socks.register(self.upipe, select.POLLIN)
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        self.running = True
        while self.running:
            for (fd,flags) in self.socks.poll(100):
                if flags & select.POLLIN:
                    if fd in self.pipes:
                        self.recvpipe(self.pipes[fd])
 
    def stop(self):
        self.running = False

    def sendudpmsgto(self,msg,addr):
        self.upipe.sendmsgto(msg,addr)

    def recvpipe(self,pipe):
        try:
            pipe.fillbuf()
            while pipe.hasmsg():
                mesg = pipe.getmsg()
                self.recvmsg(mesg)
        except Exception as err:
            errhandler('RPC::recvpipe: Unable to decode', err)
    
    def recvmsg(self,mesg):
        try:
            data = json.loads(mesg)
            Type = data.get('Type')
            if Type in self.handler:
                self.handler[Type](data)
            elif Type == 'RPC':
                func = data.get('Func')
                seqn = data.get('Seqn')
                hand = f'RPC:{func}:{seqn}'
                if hand in self.handler:
                    self.handler[hand](data)

        except Exception as err:
            errhandler('RPC::recvmsg: Invalid message received: {}'.format(mesg), err)
            
    def add_device(self,dev):
        self.lock.acquire()
        self.socks.register(dev.pipe.sock, select.POLLIN)
        self.pipes[dev.pipe.fileno()] = dev.pipe
        self.lock.release()

    def del_device(self,dev):
        self.lock.acquire()
        self.socks.unregister(dev.pipe.sock)
        self.pipes.pop(dev.pipe.fileno(),None)
        self.lock.release()

    def register(self,name,func):
        self.lock.acquire()
        self.handler[name] = func
        self.lock.release()

    def unregister(self,name):
        self.lock.acquire()
        self.handler.pop(name,None)
        self.lock.release()
        
    def get_seqnum(self):
        self.lock.acquire()
        seqn = self.seqnum
        self.seqnum += 1
        self.lock.release()
        return seqn

    
    ## Remote function call

    def init_call(self,func,seqn):
        self.lock.acquire()
        self.calls[seqn] = {}
        self.calls[seqn]['data'] = {}
        self.calls[seqn]['wait'] = threading.Event()
        self.lock.release()
        self.register(f'RPC:{func}:{seqn}', self.handle_call_return)

    def finish_call(self,func,seqn):
        self.unregister(f'RPC:{func}:{seqn}')
        self.lock.acquire()
        self.calls.pop(seqn,None)
        self.lock.release()

    def wait_call_return(self,func,seqn,time=1.0):
        data = {}
        if seqn in self.calls:
            self.calls[seqn]['wait'].wait(time)
        if seqn in self.calls:
            data = self.calls[seqn]['data']
        self.finish_call(func,seqn)
        return data

    def handle_call_return(self,data):
        seqn = data['Seqn']
        if seqn in self.calls:
            self.calls[seqn]['data'] = data
            self.calls[seqn]['wait'].set()

    def call(self,rem,Func,**kwargs):
        Seqn = self.get_seqnum()
        self.init_call(Func,Seqn)
        rem.sendargs(Type='RPC',Func=Func,Seqn=Seqn,Args=kwargs)
        data = self.wait_call_return(Func,Seqn)
        return data.get('Args',{})

    def call_void(self,rem,Func,**kwargs):
        seqn = self.get_seqnum()
        rem.sendargs(Type='RPC',Func=Func,Seqn=seqn,Args=kwargs)



class Blink():

    def __init__(self,anchor,bid,src,frame,times,tinfo):
        self.anchor = anchor
        self.bid    = bid
        self.src    = src
        self.frame  = frame
        self.times  = times
        self.tinfo  = tinfo
        self.swts   = times['swts']
        self.hwts   = times['hwts']
        self.hires  = times['hires']
        self.rawts  = tinfo['rawts']

    def is_rx(self):
        return (self.tinfo['lqi'] > 0)

    def timestamp(self):
        return self.times.hires

    def get_rx_level(self):
        POW = self.tinfo['cir_pwr']
        RXP = self.tinfo['rxpacc']
        if POW>0 and RXP>0:
            level = (POW << 17) / (RXP*RXP)
            return level
        return None

    def get_fp_level(self):
        FP1 = self.tinfo['fp_ampl1']
        FP2 = self.tinfo['fp_ampl2']
        FP3 = self.tinfo['fp_ampl3']
        RXP = self.tinfo['rxpacc']
        if FP1>0 and FP2>0 and FP3>0 and RXP>0:
            level = (FP1*FP1 + FP2*FP2 + FP3*FP3) / (RXP*RXP)
            return level
        return None

    def get_xtal_ratio(self):
        I = self.tinfo['ttcki']
        O = self.tinfo['ttcko']
        if O & 0x040000:
            O -= 0x080000
        if I:
            return O/I
        return None


class Blinks():

    def __init__(self,rpc):
        self.rpc = rpc
        self.bid = 1
        self.blinks = {}
        self.timer = Timer()
        self.verbose = 0
        rpc.register('TX', self.handle_blink)
        rpc.register('RX', self.handle_blink)

    def stop(self):
        pass

    def time(self):
        return self.timer.get()

    def nap(self,delay):
        return self.timer.nap(delay)

    def sync(self,delay=0):
        return self.timer.sync(delay)
        
    def get_euis_at(self,index,direction):
        euis = []
        if index is not None:
            if index in self.blinks:
                for eui in self.blinks[index]['anchors']:
                    if self.blinks[index]['anchors'][eui]['dir'] == direction:
                        euis.append(eui)
        return euis

    def get_blink(self,index,rem):
        if isinstance(rem,DW1000):
            rem = rem.eui
        return self.blinks[index]['anchors'][rem]
    
    def get_blink_time(self,index):
        return self.blinks[index]['time']

    def get_times(self,index,rem):
        return self.get_blink(index,rem).times

    def get_swts(self,index,rem):
        return self.get_blink(index,rem).swts

    def get_hwts(self,index,rem):
        return self.get_blink(index,rem).hwts

    def get_hires(self,index,rem):
        return self.get_blink(index,rem).hires

    def get_timestamp(self,index,rem):
        return self.get_blink(index,rem).hires

    def get_rawts(self,index,rem):
        return self.get_blink(index,rem).rawts

    def get_tinfo(self,index,rem,attr):
        return self.get_blink(index,rem).tinfo

    def get_tinfo_attr(self,index,rem,attr):
        return self.get_blink(index,rem).tinfo[attr]

    def get_lqi(self,index,rem):
        return self.get_tinfo_attr(index,rem,'lqi')

    def get_snr(self,index,rem):
        return self.get_tinfo_attr(index,rem,'snr')

    def get_noise(self,index,rem):
        return self.get_tinfo_attr(index,rem,'noise')

    def get_xtal_ratio(self,index,rem):
        return self.get_blink(index,rem).get_xtal_ratio()

    def get_rx_level(self,index,rem):
        return self.get_blink(index,rem).get_rx_level()

    def get_fp_level(self,index,rem):
        return self.get_blink(index,rem).get_fp_level()

    def get_temp(self,index,rem):
        raw = self.get_tinfo_attr(index,rem,'temp')
        if raw > 32767:
            raw -= 65536
        return 0.01*raw

    def get_volt(self,index,rem):
        raw = self.get_tinfo_attr(index,rem,'volt')
        return 0.001*raw


    def create_blink(self):
        bid = self.bid
        self.bid += 1
        self.blinks[bid] = {
            'anchors' : {},
            'time'    : '{:.6f}'.format(self.time()),
            'wait'    : threading.Condition(),
        }
        return bid

    def purge_blink(self,bid):
        self.blinks.pop(bid,None)

    def blink(self,rem):
        bid = self.create_blink()
        rem.sendargsudp(Type='BEACON', Beacon=f'{bid:08x}', SubType=9)
        return bid

    def blink_bid(self,rem,bid):
        rem.sendargsudp(Type='BEACON', Beacon=f'{bid:08x}', SubType=9)
   
    def blinks_accounted_for(self,bids,ancs):
        for bid in bids:
            for anc in ancs:
                if anc.eui not in self.blinks[bid]['anchors']:
                    return bid
        return 0
        
    def wait_blinks(self,bids,ancs,wait=1.0):
        until = time.time() + wait
        delay = (until - time.time()) / 2
        missing = 1
        while missing and delay > 0.0001:
            missing = self.blinks_accounted_for(bids,ancs)
            if missing:
                with self.blinks[missing]['wait']:
                    self.blinks[missing]['wait'].wait(delay)
            delay = (until - time.time()) / 2
        if self.verbose > 0:
            for bid in bids:
                for anc in ancs:
                    if anc.eui not in self.blinks[bid]['anchors']:
                        eprint(f'wait_blinks: ID:{bid} ANCHORS:{anc.name} missing')
        

    def handle_blink(self,data):
        if self.verbose > 1:
            eprint(f'handle_blink: {data}')
        eui = data.get('Anchor')
        src = data.get('Src')
        tms = data.get('Times')
        tsi = data.get('TSInfo')
        frd = data.get('Frame')
        frm = TailFrame(bytes.fromhex(frd))
        
        if frm.tail_beacon:
            (bid,) = struct.unpack('>Q', frm.tail_beacon)
        else:
            bid = None
        
        if bid in self.blinks:
            blk = Blink(eui,bid,src,frm,tms,tsi)
            with self.blinks[bid]['wait']:
                self.blinks[bid]['anchors'][eui] = blk
                self.blinks[bid]['wait'].notify_all()


