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

from pprint import pprint
from config import *


def prints(*args, **kwargs):
    print(*args, end='', flush=True, **kwargs)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def eprints(*args, **kwargs):
    print(*args, file=sys.stderr, end='', flush=True, **kwargs)

    
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


CompSplines = {
    500: {
        16: (
             ((-95.0, -89.0), (455.2684032227685, 9.851533848614533, 0.051993231111100435)),
             ((-89.0, -81.0), (622.1582642485359, 13.601867408230925, 0.07306251852581003)),
             ((-81.0, -75.0), (-206.63577569900568, -6.862181359285285, -0.05325876022235132)),
             ((-75.0, -69.0), (-14.553074442797616, -1.7399765082001553, -0.019110731344085252)),
             ((-69.0, -61.0), (-65.34665835419767, -3.212254801451526, -0.02977941823739272)),
        ),
        64: (
              ((-105.0, -91.0), (60.352219498834565, 1.259091772638299, 0.005614160222348175)),
              (( -91.0, -81.0), (182.24644860110973, 3.938085215997636, 0.020333901101900254)),
              (( -81.0, -75.0), (416.4655048521236, 9.72127075199398, 0.05603257081757784)),
              (( -75.0, -67.0), (-235.36598188854484, -7.660900913339617, -0.05984856478355027)),
              (( -67.0, -55.0), (-15.291050806896337, -1.0915006691080062, -0.010823194973097472)),
        ),
    },
    900: {
        16: (
             ((-95.0, -89.0), (183.67480691132866, 3.6158987280067723, 0.013391462077503746)),
             ((-89.0, -81.0), (909.6294873191769, 19.92948671225841, 0.10504083084258342)),
             ((-81.0, -75.0), (-79.62234302197686, -4.496483922533177, -0.0457367625993812)),
             ((-75.0, -69.0), (47.94037800579669, -1.094811223380935, -0.023058943654632458)),
             ((-69.0, -61.0), (-95.74259549796217, -5.259534749105479, -0.05323809715869743)),
        ),
        64: (
             ((-105.0, -95.0), (216.3308306122728, 4.1714254724783855, 0.01677363406513388)),
             (( -95.0, -83.0), (148.11352408935457, 2.7353156634156304, 0.009215393273090733)),
             (( -83.0, -75.0), (732.1532410581545, 16.808623222604062, 0.09399472336764236)),
             (( -75.0, -67.0), (-20.421159267426496, -3.260069209064098, -0.039796838878970675)),
             (( -67.0, -61.0), (-96.7161189002168, -5.537443600292282, -0.0567915127387808)),
             (( -61.0, -55.0), (5.839529695372041, -2.1750623191076377, -0.029231829906617435)),
        ),
    },
}


def XSpline(spline,X):
    for S in spline:
        if S[0][0] < X <= S[0][1]:
            Y = S[1][0] + S[1][1]*X + S[1][2]*X*X
            return Y
    return None


class DW1000:

    def RxComp(Dist,CH,PRF):
        if CH in (1,2,3,5):
            BW = 500
        elif CH in (4,7):
            BW = 900
        else:
            raise ValueError
        if PRF not in (16,64):
            raise ValueError
        Spl = CompSplines[BW][PRF]
        Cor = XSpline(Spl,Dist) / 100
        return Cor

    def RxCompTime(Dist,CH,PRF):
        return DW1000.RxComp(Dist,CH,PRF) / C_AIR

    def RxCompNs(Dist,CH,PRF):
        return DW1000.RxCompTime(Dist,CH,PRF) * 1E9

    def RxCompRaw(Dist,CH,PRF):
        return DW1000.RxCompTime(Dist,CH,PRF) * DW1000_CLOCK_HZ


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

    def Pwr2Hex(val):
        loc = val.find('+')
        if loc > 0:
            a = float(val[:loc])
            b = float(val[loc:])
            c = int(a / 3)
            d = int(b * 2)
            if c<0 or c>6:
                raise ValueError
            if int(a) != 3*c:
                raise ValueError
            if d<0 or d>31:
                raise ValueError
            if b != d/2:
                raise ValueError
            e = (6 - c) << 5
            return (e|d)
        else:
            a = int(val,0)
            if a<0:
                raise ValueError
            return a

    def TxPower(val):
        if isinstance(val,str):
            n = val.count(':')
            if n == 3:
                N = val.findall(':')
                A = DW1000.Pwr2Hex(val[:N[0]])
                B = DW1000.Pwr2Hex(val[N[0]+1,N[1]])
                C = DW1000.Pwr2Hex(val[N[1]+1,N[2]])
                D = DW1000.Pwr2Hex(val[N[2]+1:])
                if A>255 or B>255 or C>255 or D>255:
                    raise ValueError
                return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,B,C,D)
            elif n == 1:
                N = val.find(':')
                A = DW1000.Pwr2Hex(val[:N])
                B = DW1000.Pwr2Hex(val[N+1:])
                if A>255 or B>255:
                    raise ValueError
                return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,A,B,B)
            elif n == 0:
                A = DW1000.Pwr2Hex(val)
                if A<256:
                    return '0x{:02x}{:02x}{:02x}{:02x}'.format(A,A,A,A)
                else:
                    return '0x{:08x}'.format(A)
                raise ValueError
        else:
            return val

    CONV = {
        'tx_power':  TxPower,
    }

    # Order is important
    ATTRS = (
        'channel',
        'pcode',
        'prf',
        'rate',
        'txpsr',
        'smart_power',
        'tx_power',
        'xtalt',
        'antd',
        'snr_threshold',
        'fpr_threshold',
        'noise_threshold',
    )

    def __init__(self,host,port,rpc):
        self.rpc  = rpc
        self.host = host
        self.addr = socket.getaddrinfo(host, port, socket.AF_INET6)[0][4]
        self.eui  = rpc.getEUI(self.addr)

    def GetCoord(self):
        return DW1000_DEVICE_CALIB[self.eui]['coord']

    def GetAttr(self,attr):
        return self.rpc.getAttr(self.addr,attr)

    def SetAttr(self,attr,value):
        if attr in self.CONV:
            value = self.CONV[attr](value)
        return self.rpc.setAttr(self.addr,attr,value)

    def GetAttrDefault(self,attr):
        if self.eui in DW1000_DEVICE_CALIB and attr in DW1000_DEVICE_CALIB[self.eui]:
            val = DW1000_DEVICE_CALIB[self.eui][attr]
        elif attr in DW1000_DEFAULT_CONFIG:
            val = DW1000_DEFAULT_CONFIG[attr]
        else:
            val = None
        return val

    def PrintAttrs(self):
        eprint('{} <{}>'.format(self.host,self.eui))
        for attr in DW1000.ATTRS:
            value = self.GetAttr(attr)
            eprint('  {:20s}: {}'.format(attr, value))
    
    def PrintAllRemoteAttrs(remotes):
        for remote in remotes:
            remote.PrintAttrs()
                
    def AddPrintArguments(parser):
        parser.add_argument('--print-eui', action='store_true', default=False, help='Print EUI64 value')
        for attr in DW1000.ATTRS:
            parser.add_argument('--print-'+attr, action='store_true', default=False, help='Print attribute <{}> value'.format(attr))

    def HandlePrintArguments(args,remotes):
        ret = False
        for rem in remotes:
            if getattr(args, 'print_eui'):
                print(rem.eui)
            for attr in DW1000.ATTRS:
                if getattr(args, 'print_'+attr):
                    val = rem.GetAttr(attr)
                    ret = True
                    print(val)
        return ret
    
    def AddParserArguments(parser):
        parser.add_argument('--reset', action='store_true', default=False)
        for attr in DW1000.ATTRS:
            parser.add_argument('--' + attr, type=str, default=None)

    def HandleArguments(args,remotes):
        for rem in remotes:
            for attr in DW1000.ATTRS:
                val = None
                if getattr(args,attr) is not None:
                    if getattr(args,attr) == 'cal':
                        val = rem.GetAttrDefault(attr)
                    else:
                        val = getattr(args,attr)
                elif args.reset:
                    val = rem.GetAttrDefault(attr)
                if val is not None:
                    rem.SetAttr(attr, val)


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


class RPC:
    
    def __init__(self,bind):
        self.running = True
        self.seqnum = 1
        self.handler = {}
        self.pending = {}
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(bind)
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        while self.running:
            rset,wset,eset = select.select([self.sock],[],[],0.1)
            if self.sock in rset:
                self.recv()

    def stop(self):
        self.running = False

    def recv(self):
        (msg, rem) = self.sock.recvfrom(4096)
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
    
    def send(self,dest,func,args,seqn=0):
        msg = {
            'func': func,
            'args': args,
            'seqn': seqn
        }
        data = json.dumps(msg).encode()
        self.sock.sendto(data, dest)

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

    def call(self,dest,func,args,wait=1.0):
        seqn = self.getSeqNum()
        self.initRet(func,seqn)
        self.send(dest,func,args,seqn)
        data = self.waitRet(func,seqn,wait)
        return data.get('args',{})

    def getAttr(self,addr,attr):
        return self.call(addr, 'getAttr', { 'attr': attr }).get('value',None)

    def setAttr(self,addr,attr,val):
        return self.call(addr, 'setAttr', { 'attr': attr, 'value': val }).get('value',None)

    def getEUI(self,addr):
        return self.call(addr, 'getEUI', { }).get('value',None)



class Blinker():

    def __init__(self,rpc,debug=0):
        self.DEBUG = debug
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

    def Blink(self,addr,time):
        bid = self.GetBlinkId(time)
        self.rpc.send(addr, 'blink', {'bid':bid} )
        return bid

    def BlinkID(self,addr,bid):
        self.rpc.send(addr, 'blink', {'bid':bid} )
   
    def TriggerBlink(self,addr,bid,pid):
        self.rpc.send(addr, 'autoBlink', {'recv':bid, 'xmit':pid})

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
        if self.DEBUG > 0:
            pprint(data)
        try:
            args = data['args']
            eui = args.get('anchor')
            tag = args.get('tag')
            tsi = args.get('tsi',None)
            tss = int(args.get('tss'),16)
            bid = int(args.get('bid'))
        except:
            eprint('BlinkRecv: data missing')
            return
        if bid in self.blinks:
            with self.blinks[bid]['wait']:
                self.blinks[bid]['anchors'][eui] = {}
                self.blinks[bid]['anchors'][eui]['tag'] = tag
                self.blinks[bid]['anchors'][eui]['tss'] = tss
                self.blinks[bid]['anchors'][eui]['tsi'] = tsi
                self.blinks[bid]['anchors'][eui]['dir'] = 'RX'
                self.blinks[bid]['wait'].notify_all()

    def BlinkXmit(self,data):
        if self.DEBUG > 0:
            pprint(data)
        try:
            args = data['args']
            eui = args.get('anchor')
            tag = args.get('tag')
            tsi = args.get('tsi',None)
            tss = int(args.get('tss'),16)
            bid = int(args.get('bid'))
        except:
            eprint('BlinkXmit: data missing')
            return
        if bid in self.blinks:
            with self.blinks[bid]['wait']:
                self.blinks[bid]['anchors'][eui] = {}
                self.blinks[bid]['anchors'][eui]['tag'] = tag
                self.blinks[bid]['anchors'][eui]['tss'] = tss
                self.blinks[bid]['anchors'][eui]['tsi'] = tsi
                self.blinks[bid]['anchors'][eui]['dir'] = 'TX'
                self.blinks[bid]['wait'].notify_all()

    def BlinkDump(self,data):
        pprint(data)

