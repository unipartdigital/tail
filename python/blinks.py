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

from tail import *
from dwarf import *


class Timer:

    SLEEP_MIN = 500E-6   # 500us
    
    def __init__(self):
        self.start = time.time()
        self.timer = self.start

    def get(self):
        return self.timer - self.start
    
    def nap(self,delta):
        self.timer += delta
        while True:
            sleep = self.timer - time.time()
            if sleep < Timer.SLEEP_MIN:
                break
            time.sleep(sleep/2)
        return self.get()

    def sync(self):
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

    def disconnect(self):
        self.rpc.del_device(self)
        self.pipe.close()
        self.pipe = None

    def sendmsg(self,msg):
        self.pipe.sendmsg(msg)
        
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
        c = int(lst[0]) / 3
        d = int(lst[1]) * 2
        if c<0 or c>6:
            raise ValueError
        if d<0 or d>31:
            raise ValueError
        c = (6 - c) << 5
        return (c|d)

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
            c = (6 - c) << 5
            return (c|d)
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
        if isinstance(psr,str):
            psr = int(psr)
        if psr in (64,128,256,512,1024,2048,4096):
            return psr
        raise ValueError(f'Invalid PSR {psr}')
    
    def validate_rate(rate):
        if isinstance(rate,str):
            rate = int(rate)
        if rate in (110,850,6800):
            return rate
        raise ValueError(f'Invalid rate {rate}')

    def validate_prf(prf):
        if isinstance(prf,str):
            prf = int(prf)
        if prf in (16,64):
            return prf
        raise ValueError(f'Invalid PRF {prf}')

    def validate_channel(ch):
        if isinstance(ch,str):
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
    
    def __init__(self):
        self.running = False
        self.seqnum = 1
        self.pipes = {}
        self.fdset = set()
        self.calls = {}
        self.handler = {}
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        self.running = True
        while self.running:
            (rset,wset,eset) = select.select(list(self.fdset),[],[],0.1)
            for rsock in rset:
                if rsock in self.pipes:
                    pipe = self.pipes[rsock]
                    pipe.fillmsg()
                    while pipe.hasmsg():
                        self.recvmsg(pipe.getmsg())

    def stop(self):
        self.running = False
        
    def recvmsg(self,mesg):
        try:
            data = json.loads(mesg)
            #eprint(f'recvmsg: {data}')
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
            errhandler('Invalid RPC message received', err)
            
    def sendmsg(self,dev,**kwargs):
        mesg = json.dumps(kwargs)
        dev.sendmsg(mesg)

    def add_device(self,dev):
        self.lock.acquire()
        self.fdset.add(dev.pipe.sock)
        self.pipes[dev.pipe.sock] = dev.pipe
        self.lock.release()

    def del_device(self,dev):
        self.lock.acquire()
        self.fdset.discard(dev.pipe.sock)
        self.pipes.pop(dev.pipe.sock,None)
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

    def call(self,dev,Func,**kwargs):
        Seqn = self.get_seqnum()
        self.init_call(Func,Seqn)
        self.sendmsg(dev,Type='RPC',Func=Func,Seqn=Seqn,Args=kwargs)
        data = self.wait_call_return(Func,Seqn)
        return data.get('Args',{})

    def call_void(self,dev,Func,**kwargs):
        seqn = self.get_seqnum()
        self.sendmsg(dev,Type='RPC',Func=Func,Seqn=seqn,Args=kwargs)



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
        rpc.register('TX', self.handle_blink)
        rpc.register('RX', self.handle_blink)

    def stop(self):
        pass

    def time(self):
        return self.timer.get()

    def nap(self,delay):
        return self.timer.nap(delay)

    def sync(self):
        return self.timer.sync()
        
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
            key = rem.name
            rem = rem.eui
        else:
            key = rem
        try:
            return self.blinks[index]['anchors'][rem]
        except KeyError:
            raise IndexError(key[-1:])
    
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
        self.rpc.sendmsg(rem, Type='BEACON', Beacon=f'{bid:08x}', SubType=9)
        return bid

    def blink_bid(self,rem,bid):
        self.rpc.sendmsg(rem, Type='BEACON', Beacon=f'{bid:08x}', SubType=9)
   
    def blinks_accounted_for(self,bid,ancs):
        return all( anc.eui in self.blinks[bid]['anchors'] for anc in ancs )
        
    def wait_blinks(self,bids,ancs,wait=1.0):
        until = time.time() + wait
        for bid in bids:
            with self.blinks[bid]['wait']:
                while not self.blinks_accounted_for(bid,ancs):
                    delay = until - time.time()
                    if delay < 0.0001:
                        raise TimeoutError
                    self.blinks[bid]['wait'].wait(delay/2)
        
    def handle_blink(self,data):
        try:
            eui = data.get('Anchor')
            src = data.get('Src')
            tms = data.get('Times')
            tsi = data.get('TSInfo')
            frd = data.get('Frame')
            frm = TailFrame(bytes.fromhex(frd))
            (bid,) = struct.unpack('>Q', frm.tail_beacon)

            if bid in self.blinks:
                blk = Blink(eui,bid,src,frm,tms,tsi)
                with self.blinks[bid]['wait']:
                    self.blinks[bid]['anchors'][eui] = blk
                    self.blinks[bid]['wait'].notify_all()
        
        except Exception as err:
            errhandler('handle_blink', err)
