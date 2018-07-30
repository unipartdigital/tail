#!/usr/bin/python3
#
# Helper functions/classes/code for Tail algorithm development
#

import pprint
import ipaddress
import netifaces
import socket
import select
import ctypes
import json
import threading
import queue
import time
import sys


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)



class DW1000:

    ATTRS = {
        'channel'	  : 7,
        'rate'		  : 6800,
        'prf'		  : 64,
        'pcode'		  : 20,
        'txpsr'		  : 64,
        'antd'		  : None,
        'xtalt'		  : None,
        'tx_power'        : None,
        'smart_power'     : 1,
        'snr_threshold'   : 1,
        'fpr_threshold'   : 1,
        'noise_threshold' : 256,
    }


    def AddParserOptions(parser):
        parser.add_argument('--reset', action='store_true', default=False)
        parser.add_argument('--channel',		type=str, default=None)
        parser.add_argument('--rate',			type=str, default=None)
        parser.add_argument('--prf',			type=str, default=None)
        parser.add_argument('--pcode',			type=str, default=None)
        parser.add_argument('--txpsr',			type=str, default=None)
        parser.add_argument('--antd',			type=str, default=None)
        parser.add_argument('--xtalt',			type=str, default=None)
        parser.add_argument('--tx_power',		type=str, default=None)
        parser.add_argument('--smart_power',		type=str, default=None)
        parser.add_argument('--snr_threshold',		type=str, default=None)
        parser.add_argument('--fpr_threshold',		type=str, default=None)
        parser.add_argument('--noise_threshold',	type=str, default=None)

    def HandleArguments(args, rpc, remaddrs):
        if args.reset:
            for addr in remaddrs:
                for attr in DW1000.ATTRS:
                    if DW1000.ATTRS[attr] is not None:
                        rpc.setAttr(addr, attr, DW1000.ATTRS[attr])
        
        for addr in remaddrs:
            if args.channel is not None:
                rpc.setAttr(addr, 'channel', args.channel)
            if args.rate is not None:
                rpc.setAttr(addr, 'rate', args.rate)
            if args.prf is not None:
                rpc.setAttr(addr, 'prf', args.prf)
            if args.pcode is not None:
                rpc.setAttr(addr, 'pcode', args.pcode)
            if args.txpsr is not None:
                rpc.setAttr(addr, 'txpsr', args.txpsr)
            if args.antd is not None:
                rpc.setAttr(addr, 'antd', int(args.antd,0))
            if args.xtalt is not None:
                rpc.setAttr(addr, 'xtalt', int(args.xtalt,0))
            if args.tx_power is not None:
                rpc.setAttr(addr, 'tx_power', int(args.tx_power,16))
            if args.smart_power is not None:
                rpc.setAttr(addr, 'smart_power', args.smart_power)
            if args.snr_threshold is not None:
                rpc.setAttr(addr, 'snr_threshold', args.snr_threshold)
            if args.fpr_threshold is not None:
                rpc.setAttr(addr, 'fpr_threshold', args.fpr_threshold)
            if args.noise_threshold is not None:
                rpc.setAttr(addr, 'noise_threshold', args.noise_threshold)

    def PrintRemoteAttrs(rpc,addr):
        for attr in DW1000.ATTRS:
            val = rpc.getAttr(addr, attr)
            eprint('  {:20s}: {}'.format(attr, val))
        
    

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

    def getAttr(self,rem,attr):
        return self.call(rem, 'getAttr', { 'attr': attr }).get('value',None)

    def setAttr(self,rem,attr,val):
        return self.call(rem, 'setAttr', { 'attr': attr, 'value': val }).get('value',None)

    def getEUI(self,rem):
        return self.call(rem, 'getEUI', { }).get('value',None)



class Blinker():

    tsinfo_attrs = (
        'rawts',
        'lqi',
        'snr',
        'fpr',
        'noise',
        'rxpacc',
        'fp_index',
        'fp_ampl1',
        'fp_ampl2',
        'fp_ampl3',
        'cir_pwr',
        'fp_pwr',
        'ttcko',
        'ttcki',
    )

    def __init__(self,rpc,rxs):
        self.rpc = rpc
        self.rxs = rxs
        self.bid = 1
        self.blinks = {}
        self.waiting = {}
        self.pqueue = queue.Queue()
        self.pthread = threading.Thread(target=self.print_run)
        rpc.register('blinkRecv', self.BlinkRecv)
        rpc.register('blinkXmit', self.BlinkXmit)
        self.pthread.start()

    def stop(self):
        self.pqueue.put(None)
        self.pqueue.join()

    def GetBlinkId(self,time):
        bid = self.bid
        self.blinks[bid] = { '__time__': '{:.6f}'.format(time) }
        self.bid += 1
        return bid

    def Blink(self,remote,time):
        bid = self.GetBlinkId(time)
        self.rpc.send(remote, 'blink', {'bid':bid} )
        return bid

    def BlinkID(self,remote,bid):
        self.rpc.send(remote, 'blink', {'bid':bid} )
   
    def BlinkWait(self,remote,bid,wait=1.0):
        self.waiting[bid] = threading.Event()
        self.Blink(self,remote,bid)
        self.waiting[bid].wait(wait)
        del self.waiting[bid]

    
    def PingPong(self,remote,bid,pid):
        self.rpc.send(remote, 'pingPong', {'ping':bid, 'pong':pid})

    
    def BlinkRecv(self,data):
        try:
            args = data['args']
            anc = args.get('anchor')
            tag = args.get('tag')
            tsi = args.get('tsi',None)
            tss = int(args.get('tss'),16)
            bid = int(args.get('bid'))
        except:
            #eprint('BlinkRecv: data missing')
            return

        if bid in self.blinks:
            self.blinks[bid][anc] = {}
            self.blinks[bid][anc]['tag'] = tag
            self.blinks[bid][anc]['tss'] = tss
            self.blinks[bid][anc]['tsi'] = tsi
            self.blinks[bid][anc]['dir'] = 'RX'


    def BlinkXmit(self,data):
        try:
            args = data['args']
            anc = args.get('anchor')
            tag = args.get('tag')
            tsi = args.get('tsi',None)
            tss = int(args.get('tss'),16)
            bid = int(args.get('bid'))
        except:
            #eprint('BlinkXmit: data missing')
            return

        if bid in self.blinks:
            self.blinks[bid][anc] = {}
            self.blinks[bid][anc]['tag'] = tag
            self.blinks[bid][anc]['tss'] = tss
            self.blinks[bid][anc]['tsi'] = tsi
            self.blinks[bid][anc]['dir'] = 'TX'
        
        if bid in self.waiting:
            self.waiting[bid].set()

    def BlinkDump(self,data):
        pprint.pprint(data)

    def print_run(self):
        while True:
            item = self.pqueue.get()
            self.pqueue.task_done()
            if item is None:
                break
            self.dump(**item)

    def print(self,index):
        self.pqueue.put({'index':index})

    def dump(self, index=None):
        blinks = self.blinks
        if index in blinks:
            msg = '{},{}'.format(index,blinks[index].get('__time__',''))
            for anc in self.rxs:
                eui = anc['EUI']
                if eui in blinks[index]:
                    TI = blinks[index][eui]['tsi']
                    if blinks[index][eui]['dir'] == 'TX':
                        TX = blinks[index][eui]['tss']
                        RX = ''
                    else:
                        RX = blinks[index][eui]['tss']
                        TX = ''
                else:
                    RX = ''
                    TX = ''
                    TI = {}
                msg += ',{},{}'.format(TX,RX)
                for attr in self.tsinfo_attrs:
                    msg += ',{}'.format(TI.get(attr,''))

            print(msg)
            
            del self.blinks[index]


