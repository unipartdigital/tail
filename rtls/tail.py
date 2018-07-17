#!/usr/bin/python3
#
# Test hack for developing RPi Tail algorithms
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
        rid = self.seqnum
        self.seqnum += 1
        self.lock.release()
        return rid
                
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
        return self.call(rem, 'getAttr', { 'attr': attr } ).get('value',None)

    def setAttr(self,rem,attr,val):
        return self.call(rem, 'setAttr', { 'attr': attr, 'value': val } ).get('value',None)

    def getEUI(self,rem):
        return self.call(rem, 'getEUI', { } ).get('value',None)



class Blinker():

    def __init__(self,rpc,rxs):
        self.rpc = rpc
        self.rxs = rxs
        self.bid = 1
        self.blinks = {}
        self.waiting = {}
        self.bqueue = queue.Queue()
        self.pqueue = queue.Queue()
        self.bthread = threading.Thread(target=self.blink_run)
        self.pthread = threading.Thread(target=self.print_run)
        rpc.register('blinkRecv', self.BlinkRecv)
        rpc.register('blinkXmit', self.BlinkXmit)
        self.pthread.start()
        self.bthread.start()

    def blink_run(self):
        while True:
            item = self.bqueue.get()
            self.bqueue.task_done()
            if item is None:
                break
            self.BlinkWork(**item)

    def stop(self):
        self.bqueue.put(None)
        self.pqueue.put(None)
        self.bqueue.join()
        self.pqueue.join()

    def GetBlinkId(self,time):
        bid = self.bid
        self.blinks[bid] = { '__time__': time }
        self.bid += 1
        return bid

    def Blink(self,remote,time,wait=None):
        bid = self.GetBlinkId(time)
        self.bqueue.put({'remote':remote, 'wait':wait, 'bid':bid})
        return bid
    
    def BlinkWork(self,remote=None,wait=None,bid=None):
        if remote is not None:
            if wait is not None:
                self.waiting[bid] = threading.Event()
            self.rpc.send(remote, 'blink', {'bid':bid} )
            if wait is not None:
                self.waiting[bid].wait(wait)
                del self.waiting[bid]

    def BlinkRecv(self,data):
        try:
            args = data['args']
            anc = args['anchor']
            tag = args['tag']
            tss = int(args['tss'],16)
            bid = int(args['bid'])
        except:
            eprint('BlinkRecv: data missing')
            return
        
        self.blinks[bid][anc] = {}
        self.blinks[bid][anc]['tag'] = tag
        self.blinks[bid][anc]['tss'] = tss
        self.blinks[bid][anc]['dir'] = 'RX'


    def BlinkXmit(self,data):
        try:
            args = data['args']
            anc = args['anchor']
            tag = args['tag']
            tss = int(args['tss'],16)
            bid = int(args['bid'])
        except:
            eprint('BlinkXmit: data missing')
            return
        
        self.blinks[bid][anc] = {}
        self.blinks[bid][anc]['tag'] = tag
        self.blinks[bid][anc]['tss'] = tss
        self.blinks[bid][anc]['dir'] = 'TX'
        if bid in self.waiting:
            self.waiting[bid].set()


    def print_run(self):
        while True:
            item = self.pqueue.get()
            self.pqueue.task_done()
            if item is None:
                break
            self.dump(**item)

    def print(self,index):
        if index in self.blinks:
            self.pqueue.put({'index':index})

    def dump(self, index=None):
        blinks = self.blinks
        if index in blinks:
            msg = '{},{}'.format(index,blinks[index]['__time__'])
            for anc in self.rxs:
                eui = anc['EUI']
                if eui in blinks[index]:
                    if blinks[index][eui]['dir'] == 'TX':
                        TX = blinks[index][eui]['tss']
                        RX = ''
                    else:
                        RX = blinks[index][eui]['tss']
                        TX = ''
                else:
                    RX = ''
                    TX = ''
                msg += ',{},{}'.format(TX,RX)

            print(msg)
            
            del self.blinks[index]


