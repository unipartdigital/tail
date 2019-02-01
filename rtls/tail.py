#!/usr/bin/python3
#
# Helper functions/classes/code for Tail algorithm development
#

import sys
import math
import time
import queue
import json
import ctypes
import socket
import select
import ipaddress
import netifaces
import threading

import numpy as np
import numpy.linalg as lin
import scipy.interpolate as interp

from config import *
from pprint import pprint


VERBOSE = 0
DEBUG = 0


def prints(*args, **kwargs):
    print(*args, end='', flush=True, **kwargs)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def eprints(*args, **kwargs):
    print(*args, file=sys.stderr, end='', flush=True, **kwargs)

def vprint(level, *args, **kwargs):
    if VERBOSE >= level:
        print(*args, file=sys.stderr, **kwargs)

def veprint(level, *args, **kwargs):
    if VERBOSE >= level:
        print(*args, file=sys.stderr, **kwargs)

def veprints(level, *args, **kwargs):
    if VERBOSE >= level:
        prints(*args, file=sys.stderr, **kwargs)

    
def frange(a,b,c):
    L = b-a
    N = int(L/c)
    #D = [ (x/N)*L+a for x in range(N+1) ]
    #R = np.array(D)
    R = np.linspace(a,b,N+1)
    return R

def fpeak(delays, drange=5.0, dwin=0.25, threshold=0.75 ):
    Data = np.array(delays)
    Davg = np.mean(Data)
    Dstd = np.std(Data)
    a = Davg - drange * Dstd
    b = Davg + drange * Dstd
    c = Dstd * dwin
    R = frange(a,b,c)
    ranges = []
    for I in range(len(R)):
        r = R[I]
        N = 0
        for x in Data:
            if r-c < x < r+c:
                N += 1
        ranges.append(N)
    Rmax = max(ranges)
    Rlim = threshold * Rmax
    for I in range(len(R)):
        if ranges[I] > Rlim:
            break
    r = R[I]
    Wdat = Data[ (r-c < Data) & (Data < r+c) ]
    Wavg = np.mean(Wdat)
    Wstd = np.std(Wdat)
    return (Wavg,Wstd)


DATA = np.array(DW1000_RX_POWER_TABLE) / 40 - 105

RFP1 = interp.LSQUnivariateSpline(DATA[:,1],DATA[:,0],[10.0-105,20.0-105])
RFP2 = interp.LSQUnivariateSpline(DATA[:,2],DATA[:,0],[10.0-105,22.5-105])
RFP3 = interp.LSQUnivariateSpline(DATA[:,3],DATA[:,0],[10.0-105,22.5-105])


def XSpline(spline,X):
    for S in spline:
        if S[0][0] < X <= S[0][1]:
            Y = S[1][0] + S[1][1]*X + S[1][2]*X*X
            return Y
    return None


class Timer:

    def __init__(self):
        self.start = time.time()
        self.timer = self.start

    def get(self):
        return self.timer - self.start
    
    def nap(self,delta):
        self.timer += delta
        while True:
            now = time.time()
            if now > self.timer:
                break
            time.sleep(self.timer - now)
        return self.get()

    def sync(self):
        self.timer = time.time()
        return self.get()


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
        pipe.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if local is not None:
            pipe.sock.bind(local)
        if remote is not None:
            pipe.sock.connect(remote)
        return pipe


class TCPPipe(TailPipe):

    def connect(remote=None, local=None):
        pipe = TCPPipe.socket(socket.AF_INET,socket.SOCK_STREAM)
        pipe.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if remote is not None:
            pipe.sock.connect(remote)
        return pipe


class DW1000:

    def __init__(self,host,port,rpc):
        self.rpc  = rpc
        self.host = host
        self.port = port
        self.addr = socket.getaddrinfo(host, port, socket.AF_INET)[0][4]
        self.pipe = TCPPipe.connect(self.addr)
        self.rpc.addPipe(self.pipe)
        self.eui = rpc.getEUI(self)

    def GetCoord(self):
        return DW1000_DEVICE_CALIB[self.eui]['coord']

    def GetDWAttr(self,attr):
        return self.rpc.getDWAttr(self,attr)

    def SetDWAttr(self,attr,value):
        if attr in self.CONV:
            value = self.CONV[attr](value)
        return self.rpc.setDWAttr(self,attr,value)

    def GetDWAttrDefault(self,attr):
        if self.eui in DW1000_DEVICE_CALIB and attr in DW1000_DEVICE_CALIB[self.eui]:
            val = DW1000_DEVICE_CALIB[self.eui][attr]
        elif attr in DW1000_DEFAULT_CONFIG:
            val = DW1000_DEFAULT_CONFIG[attr]
        else:
            val = None
        return val

    def PrintDWAttrs(self):
        eprint('{} <{}>'.format(self.host,self.eui))
        for attr in DW1000_ATTRS:
            value = self.GetDWAttr(attr)
            eprint('  {:20s}: {}'.format(attr, value))

    ##
    ## Static members
    ##

    def PrintAllRemoteAttrs(remotes,summary=False):
        if summary:
            eprints(' {:24s}'.format('HOSTS'))
            for rem in remotes:
                eprints(' {:10s}'.format(rem.host[:9]))
            for attr in DW1000_ATTRS:
                eprints('\n  {:20s}:  '.format(attr))
                for rem in remotes:
                    value = rem.GetDWAttr(attr)
                    eprints(' {:10s}'.format(str(value)))
            eprint()
        else:
            for rem in remotes:
                eprint('{} <{}>'.format(rem.host,rem.eui))
                for attr in DW1000_ATTRS:
                    value = rem.GetDWAttr(attr)
                    eprint('  {:20s}: {}'.format(attr,value))

    def AddPrintArguments(parser):
        parser.add_argument('--print-eui', action='store_true', default=False, help='Print EUI64 value')
        for attr in DW1000_ATTRS:
            parser.add_argument('--print-'+attr, action='store_true', default=False, help='Print attribute <{}> value'.format(attr))

    def HandlePrintArguments(args,remotes):
        ret = False
        for rem in remotes:
            if getattr(args, 'print_eui'):
                print(rem.eui)
            for attr in DW1000_ATTRS:
                if getattr(args, 'print_'+attr):
                    val = rem.GetDWAttr(attr)
                    ret = True
                    print(val)
        return ret
    
    def AddParserArguments(parser):
        parser.add_argument('--reset', action='store_true', default=False)
        for attr in DW1000_ATTRS:
            parser.add_argument('--' + attr, type=str, default=None)

    def HandleArguments(args,remotes):
        for rem in remotes:
            for attr in DW1000_ATTRS:
                val = None
                if getattr(args,attr) is not None:
                    if getattr(args,attr) == 'cal':
                        val = rem.GetDWAttrDefault(attr)
                    else:
                        val = getattr(args,attr)
                elif args.reset:
                    val = rem.GetDWAttrDefault(attr)
                if val is not None:
                    rem.SetDWAttr(attr, val)
    
    def RxComp(PWR,CH,PRF):
        if CH in (1,2,3,5):
            BW = 500
        elif CH in (4,7):
            BW = 900
        else:
            raise ValueError
        if PRF not in (16,64):
            raise ValueError
        Spl = DW1000_COMP_SPLINES[BW][PRF]
        Cor = XSpline(Spl,PWR) / 100
        return Cor

    def RxCompTime(PWR,CH,PRF):
        return DW1000.RxComp(PWR,CH,PRF) / C_AIR

    def RxCompNs(PWR,CH,PRF):
        return DW1000.RxCompTime(PWR,CH,PRF) * 1E9

    def RxCompRaw(PWR,CH,PRF):
        return DW1000.RxCompTime(PWR,CH,PRF) * DW1000_CLOCK_HZ

    def RxPower2dBm(power,prf=64):
        Plog = 10*math.log10(power)
        if prf == 16:
            Plog -= 113.77
            if Plog < -105:
                return Plog
            elif Plog < -82:
                return float(RFP1(Plog))
            else:
                return -65
        else:
            Plog -= 121.74
            if Plog < -105:
                return Plog
            elif Plog < -77:
                return float(RFP3(Plog))
            else:
                return -65
        raise ValueError

    def TxPowerValue(txpwr):
        n = txpwr.find('+')
        if n > 0:
            a = float(txpwr[:n])
            b = float(txpwr[n:])
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
        else:
            a = int(txpwr,0)
            return a

    def DecodeTxPower(txpwr):
        if isinstance(txpwr,int):
            return txpwr
        
        elif isinstance(txpwr,float):
            return int(txpwr) ## convert to a+b?
            
        elif isinstance(txpwr,str):
            n = txpwr.count(':')
            if n == 3:
                N = txpwr.findall(':')
                A = DW1000.TxPowerValue(txpwr[:N[0]])
                B = DW1000.TxPowerValue(txpwr[N[0]+1,N[1]])
                C = DW1000.TxPowerValue(txpwr[N[1]+1,N[2]])
                D = DW1000.TxPowerValue(txpwr[N[2]+1:])
                if A<0 or B<0 or C<0 or D<0:
                    raise ValueError
                if A>255 or B>255 or C>255 or D>255:
                    raise ValueError
                return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,B,C,D)
            elif n == 1:
                N = txpwr.find(':')
                A = DW1000.TxPowerValue(txpwr[:N])
                B = DW1000.TxPowerValue(txpwr[N+1:])
                if A<0 or B<0:
                    raise ValueError
                if A>255 or B>255:
                    raise ValueError
                return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,A,B,B)
            elif n == 0:
                A = DW1000.TxPowerValue(txpwr)
                if A<0:
                    raise ValueError
                if A<256:
                    return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,A,A,A)
                else:
                    return '0x{:08x}'.format(A)
        raise ValueError

    # Parameter value conversions
    CONV = {
        'tx_power':  DecodeTxPower,
    }


class RPC:
    
    def __init__(self,udp=None):
        self.running = True
        self.seqnum = 1
        self.fdset = set()
        self.pipes = {}
        self.handler = {}
        self.pending = {}
        if udp is not None:
            pipe = UDPPipe.connect(local=udp)
            self.addPipe(pipe)
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        while self.running:
            (rset,wset,eset) = select.select(list(self.fdset),[],[],0.1)
            for rsock in rset:
                if rsock in self.pipes:
                    pipe = self.pipes[rsock]
                    pipe.fillmsg()
                    while pipe.hasmsg():
                        self.recv(pipe.getmsg())


    def stop(self):
        self.running = False

    def recv(self,msg):
        try:
            data = json.loads(msg.decode())
            func = data.get('func')
            args = data.get('args')
            seqn = data.get('seqn')
            retf = func + '::' + str(seqn)
        except:
            eprint("Invalid RPC message received")
            return
        if retf in self.handler:
            self.handler[retf](data)
        elif func in self.handler:
            self.handler[func](data)
    
    def send(self,rem,func,args,seqn=0):
        msg = {
            'func': func,
            'args': args,
            'seqn': seqn
        }
        data = json.dumps(msg).encode()
        rem.pipe.sendmsg(data)

    def addPipe(self,pipe):
        self.fdset.add(pipe.sock)
        self.pipes[pipe.sock] = pipe

    def delPipe(self,pipe):
        self.fdset.discard(pipe.sock)
        del self.pipes[pipe.sock]

    def register(self,name,func):
        self.handler[name] = func

    def unregister(self,name):
        del self.handler[name]
        
    def getSeqNum(self):
        self.lock.acquire()
        seqn = self.seqnum
        self.seqnum += 1
        self.lock.release()
        return seqn
    
    def initRet(self,func,seqn):
        self.pending[seqn] = {}
        self.pending[seqn]['data'] = {}
        self.pending[seqn]['wait'] = threading.Event()
        self.register(func + '::ret::' + str(seqn), self.cret)

    def waitRet(self,func,seqn,time=1.0):
        data = {}
        if seqn in self.pending:
            wait = self.pending[seqn]['wait']
            wait.wait(time)
        if seqn in self.pending:
            data = self.pending[seqn]['data']
            del self.pending[seqn]
        self.unregister(func + '::ret::' + str(seqn))
        return data

    def cret(self,data):
        seqn = data['seqn']
        if seqn in self.pending:
            self.pending[seqn]['data'] = data
            self.pending[seqn]['wait'].set()

    def call(self,rem,func,args,wait=1.0):
        seqn = self.getSeqNum()
        self.initRet(func,seqn)
        self.send(rem,func,args,seqn)
        data = self.waitRet(func,seqn,wait)
        return data.get('args',{})

    def getDWAttr(self,rem,attr):
        return self.call(rem, 'getAttr', { 'attr': attr }).get('value',None)

    def setDWAttr(self,rem,attr,val):
        return self.call(rem, 'setAttr', { 'attr': attr, 'value': val }).get('value',None)

    def getEUI(self,rem):
        return self.call(rem, 'getEUI', { }).get('value',None)



class Blinker():

    def __init__(self,rpc,debug=0):
        self.rpc = rpc
        self.bid = 1
        self.blinks = {}
        rpc.register('blinkRecv', self.BlinkRecv)
        rpc.register('blinkXmit', self.BlinkXmit)

    def stop(self):
        pass

    def getEUIs(self,index,direc):
        euis = []
        if index is not None:
            if index in self.blinks:
                for eui in self.blinks[index]['anchors']:
                    if self.blinks[index]['anchors'][eui]['dir'] == direc:
                        euis.append(eui)
        return euis

    def getTime(self,index):
        return self.blinks[index]['time']

    def getTS(self,index,eui,raw=False):
        if raw:
            return self.blinks[index]['anchors'][eui]['tsi']['rawts']
        else:
            return self.blinks[index]['anchors'][eui]['tss']
        raise ValueError

    def getTSW(self,index,eui):
        return self.blinks[index]['anchors'][eui]['tsw']

    def getLQI(self,index,eui):
        if self.blinks[index]['anchors'][eui]['dir'] == 'RX':
            return self.blinks[index]['anchors'][eui]['tsi']['lqi']
        raise ValueError

    def getSNR(self,index,eui):
        if self.blinks[index]['anchors'][eui]['dir'] == 'RX':
            return self.blinks[index]['anchors'][eui]['tsi']['snr']
        raise ValueError

    def getNoise(self,index,eui):
        if self.blinks[index]['anchors'][eui]['dir'] == 'RX':
            return self.blinks[index]['anchors'][eui]['tsi']['noise']
        raise ValueError

    def getXtalPPM(self,index,eui):
        if self.blinks[index]['anchors'][eui]['dir'] == 'RX':
            TTCKI = self.blinks[index]['anchors'][eui]['tsi']['ttcki']
            TTCKO = self.blinks[index]['anchors'][eui]['tsi']['ttcko']
            if TTCKO & 0x040000:
                TTCKO -= 0x080000
            if TTCKI != 0:
                return TTCKO / TTCKI
        raise ValueError

    def getRxPower(self,index,eui):
        if self.blinks[index]['anchors'][eui]['dir'] == 'RX':
            CIRPWR = self.blinks[index]['anchors'][eui]['tsi']['cir_pwr']
            RXPACC = self.blinks[index]['anchors'][eui]['tsi']['rxpacc']
            if RXPACC>0 and CIRPWR>0:
                power = (CIRPWR << 17) / (RXPACC*RXPACC)
                return power
        raise ValueError

    def getFpPower(self,index,eui):
        if self.blinks[index]['anchors'][eui]['dir'] == 'RX':
            FPA1 = self.blinks[index]['anchors'][eui]['tsi']['fp_ampl1']
            FPA2 = self.blinks[index]['anchors'][eui]['tsi']['fp_ampl2']
            FPA3 = self.blinks[index]['anchors'][eui]['tsi']['fp_ampl3']
            RXPACC = self.blinks[index]['anchors'][eui]['tsi']['rxpacc']
            if RXPACC>0 and FPA1>0 and FPA2>0 and FPA3>0:
                power = (FPA1*FPA1 + FPA2*FPA2 + FPA3*FPA3) / (RXPACC*RXPACC)
                return power
        raise ValueError

    def getTemp(self,index,eui):
        raw = self.blinks[index]['anchors'][eui]['tsi']['temp']
        return 0.01*raw

    def getVolt(self,index,eui):
        raw = self.blinks[index]['anchors'][eui]['tsi']['volt']
        return 0.001*raw

    def GetBlinkId(self,time=0.0):
        bid = self.bid
        self.blinks[bid] = {
            'time'    : '{:.6f}'.format(time),
            'wait'    : threading.Condition(),
            'anchors' : {},
        }
        self.bid += 1
        return bid

    def PurgeBlink(self,bid):
        del self.blinks[bid]

    def Blink(self,rem,time):
        bid = self.GetBlinkId(time)
        self.rpc.send(rem, 'blink', {'bid':bid} )
        return bid

    def BlinkID(self,rem,bid):
        self.rpc.send(rem, 'blink', {'bid':bid} )
   
    def TriggerBlink(self,rem,bid,pid):
        self.rpc.send(rem, 'autoBlink', {'recv':bid, 'xmit':pid})

    def BlinksReceivedFor(self,bid,ancs):
        for anc in ancs:
            if anc.eui not in self.blinks[bid]['anchors']:
                return False
        return True
        
    def WaitBlinks(self,bids,ancs,wait=0.1):
        until = time.time() + wait
        for bid in bids:
            if bid in self.blinks:
                with self.blinks[bid]['wait']:
                    while not self.BlinksReceivedFor(bid,ancs):
                        if not self.blinks[bid]['wait'].wait(until-time.time()):
                            raise TimeoutError
    
    def BlinkRecv(self,data):
        if DEBUG > 0:
            pprint(data)
        try:
            args = data['args']
            eui = args.get('anchor')
            tag = args.get('tag')
            tsi = args.get('tsi',None)
            tsw = int(args.get('tsw'),16)
            tss = int(args.get('tss'),16)
            bid = int(args.get('bid'))
        except:
            #eprint('BlinkRecv: data missing')
            return
        if bid in self.blinks:
            with self.blinks[bid]['wait']:
                self.blinks[bid]['anchors'][eui] = {}
                self.blinks[bid]['anchors'][eui]['tag'] = tag
                self.blinks[bid]['anchors'][eui]['tsw'] = tsw
                self.blinks[bid]['anchors'][eui]['tss'] = tss
                self.blinks[bid]['anchors'][eui]['tsi'] = tsi
                self.blinks[bid]['anchors'][eui]['dir'] = 'RX'
                self.blinks[bid]['wait'].notify_all()

    def BlinkXmit(self,data):
        if DEBUG > 0:
            pprint(data)
        try:
            args = data['args']
            eui = args.get('anchor')
            tag = args.get('tag')
            tsi = args.get('tsi',None)
            tss = int(args.get('tss'),16)
            tsw = int(args.get('tsw'),16)
            bid = int(args.get('bid'))
        except:
            #eprint('BlinkXmit: data missing')
            return
        if bid in self.blinks:
            with self.blinks[bid]['wait']:
                self.blinks[bid]['anchors'][eui] = {}
                self.blinks[bid]['anchors'][eui]['tag'] = tag
                self.blinks[bid]['anchors'][eui]['tsw'] = tsw
                self.blinks[bid]['anchors'][eui]['tss'] = tss
                self.blinks[bid]['anchors'][eui]['tsi'] = tsi
                self.blinks[bid]['anchors'][eui]['dir'] = 'TX'
                self.blinks[bid]['wait'].notify_all()

    def BlinkDump(self,data):
        pprint(data)

