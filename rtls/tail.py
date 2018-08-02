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

from pprint import pprint
from config import *


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class DW1000:

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

    def GetAttr(self,attr):
        return self.rpc.getAttr(self.addr,attr)

    def SetAttr(self,attr,value):
        return self.rpc.setAttr(self.addr,attr,value)

    def GetAttrDefault(self,attr):
        if self.eui in DW1000_DEVICE_CONFIG and attr in DW1000_DEVICE_CONFIG[self.eui]:
            val = DW1000_DEVICE_CONFIG[eui][attr]
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
        eprint('DW1000 Attributes:')
        for remote in remotes:
            eprint()
            remote.PrintAttrs()
        eprint()
                
    def AddParserArguments(parser):
        parser.add_argument('--reset', action='store_true', default=False)
        for attr in DW1000.ATTRS:
            parser.add_argument('--' + attr, type=str, default=None)

    def HandleArguments(args,remotes):
        for rem in remotes:
            for attr in DW1000.ATTRS:
                val = None
                if getattr(args,attr) is not None:
                    if getattr(args,attr) == 'def':
                        val = rem.GetAttrDefault(attr)
                    else:
                        val = int(getattr(args,attr),0)
                elif args.reset:
                    val = rem.GetAttrDefault(attr)
                if val is not None:
                    rem.setAttr(attr, val)
                    

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

    def __init__(self,rpc,anchors=None):
        self.DEBUG = 0
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
                for anc in self.blinks[index]:
                    if 'dir' in self.blinks[index][anc]:
                        if self.blinks[index][anc]['dir'] == direc:
                            euis.append(anc)
        return euis

    def getTS(self,index,eui,raw=False):
        if raw:
            return self.blinks[index][eui]['tsi']['rawts']
        else:
            return self.blinks[index][eui]['tss']
        raise ValueError

    def getXtalPPM(self,index,eui):
        if self.blinks[index][eui]['dir'] == 'RX':
            TTCKI = self.blinks[index][eui]['tsi']['ttcki']
            TTCKO = self.blinks[index][eui]['tsi']['ttcko']
            if TTCKO & 0x040000:
                TTCKO -= 0x080000
            if TTCKI != 0:
                return TTCKO / TTCKI
        raise ValueError

    def getRFPower(self,index,eui):
        if self.blinks[index][eui]['dir'] == 'RX':
            CIRPWR = self.blinks[index][eui]['tsi']['cir_pwr']
            RXPACC = self.blinks[index][eui]['tsi']['rxpacc']
            if RXPACC > 0 and CIRPWR > 0:
                Plin = (CIRPWR << 17) / (RXPACC*RXPACC)
                Plog = 10*math.log10(Plin) - 121.74
                return Plog
        raise ValueError

    def GetBlinkId(self,time=0.0):
        bid = self.bid
        self.blinks[bid] = { '__time__': '{:.6f}'.format(time) }
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

    def BlinkRecv(self,data):
        if self.DEBUG > 0:
            pprint(data)
        try:
            args = data['args']
            anc = args.get('anchor')
            tag = args.get('tag')
            tsi = args.get('tsi',None)
            tss = int(args.get('tss'),16)
            bid = int(args.get('bid'))
        except:
            eprint('BlinkRecv: data missing')
            return
        if bid in self.blinks:
            self.blinks[bid][anc] = {}
            self.blinks[bid][anc]['tag'] = tag
            self.blinks[bid][anc]['tss'] = tss
            self.blinks[bid][anc]['tsi'] = tsi
            self.blinks[bid][anc]['dir'] = 'RX'

    def BlinkXmit(self,data):
        if self.DEBUG > 0:
            pprint(data)
        try:
            args = data['args']
            anc = args.get('anchor')
            tag = args.get('tag')
            tsi = args.get('tsi',None)
            tss = int(args.get('tss'),16)
            bid = int(args.get('bid'))
        except:
            eprint('BlinkXmit: data missing')
            return
        if bid in self.blinks:
            self.blinks[bid][anc] = {}
            self.blinks[bid][anc]['tag'] = tag
            self.blinks[bid][anc]['tss'] = tss
            self.blinks[bid][anc]['tsi'] = tsi
            self.blinks[bid][anc]['dir'] = 'TX'

    def BlinkDump(self,data):
        pprint(data)

