#!/usr/bin/python3
#
# Tail transponder.py
#

import sys
import time
import math
import json
import ctypes
import struct
import socket
import select
import argparse
import netifaces
import threading

from tail import *


class cfg():

    dw1000_profile  = 'CH5-12+6'
    dw1000_channel  = 5
    dw1000_pcode    = 12
    dw1000_prf      = 64
    dw1000_rate     = 850
    dw1000_txpsr    = 1024
    
    blink_min       = 0.002  # [s]
    blink_max       = 0.025  # [s]
    blink_count     = 1000000

    if_name         = 'wpan0'

    port            = 61777

    running         = False
    

class rxThread(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.rsock = None
        self.wait = 0
        self.lock = threading.Condition()
        
    def run(self):
        self.running = True
        self.rsock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.PROTO_IEEE802154)
        self.rsock.bind(cfg.if_bind)
        socks = select.poll()
        socks.register(self.rsock, select.POLLIN)
        while self.running:
            for (fd,flags) in socks.poll(100):
                try:
                    if fd == self.rsock.fileno():
                        if flags & select.POLLIN:
                            self.recv_frame()
                        if flags & select.POLLERR:
                            self.recv_time()
                except Exception as err:
                    pr.error('{}: {}'.format(type(err).__name__, err))
        self.rsock.close()
        cfg.running = False

    def stop(self):
        self.running = False

    def recv_time(self):
        (data,ancl,_,_) = self.rsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
        frame = TailFrame(data,ancl)
        if cfg.print_frames:
            print(frame)

    def recv_frame(self):
        (data,ancl,_,rem) = self.rsock.recvmsg(4096, 1024, 0)
        frame = TailFrame(data,ancl)
        self.lock.acquire()
        if frame.tail_protocol == 1 and frame.tail_frmtype == 1:
            if frame.tail_beacon == self.wait:
                self.wait = 0
                self.lock.notify()
        self.lock.release()
        if cfg.print_frames:
            print(frame)

    def wait_frame(self, id, timeout):
        self.lock.acquire()
        start = time.time()
        self.wait = id
        while self.wait:
            delay = timeout - (time.time() - start)
            if delay < 0.0001:
                break
            self.lock.wait(delay/4)
        self.wait = 0
        self.lock.release()
        

   
class txThread(threading.Thread):

    def __init__(self, rx):
        threading.Thread.__init__(self)
        self.running = False
        self.count = 0
        self.rx = rx

    def run(self):
        self.running = True
        while self.count < cfg.blink_count:
            for (host,pipe) in cfg.remotes.items():
                if not self.running:
                    return
                start = time.time()
                self.count += 1
                try:
                    self.send_msg(pipe, CMD='beacon', ID=self.count)
                except:
                    self.running = False
                else:
                    self.rx.wait_frame(self.count, cfg.blink_max)
                delay = cfg.blink_min - (time.time() - start)
                if delay > 0.0001:
                    time.sleep(delay)
        for (host,pipe) in cfg.remotes.items():
            try:
                self.send_msg(pipe, CMD='exit')
            except:
                pass
        cfg.running = False
    
    def stop(self):
        self.running = False

    def send_msg(self,pipe,**msg):
        pipe.sendmsg(json.dumps(msg))


def SocketLoop():

    rx = rxThread()
    tx = txThread(rx)
    
    rx.start()
    tx.start()

    cfg.running = True
    
    try:
        while cfg.running:
            time.sleep(0.1)

    except KeyboardInterrupt:
        pr.error('Exiting...')
        
    tx.stop()
    rx.stop()


def main():

    parser = argparse.ArgumentParser(description="Tag emulator")

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-C', '--csv', type=str, help='ignored')
    parser.add_argument('-I', '--interface', type=str, default=cfg.if_name)
    parser.add_argument('-i', '--interval', type=float, default=None)
    parser.add_argument('-M', '--max-interval', type=float, default=None)
    parser.add_argument('-N', '--min-interval', type=float, default=None)
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-p', '--port', type=int, default=cfg.port)
    parser.add_argument('--profile', type=str, default=None)
    parser.add_argument('--channel', type=int, default=None)
    parser.add_argument('--pcode', type=int, default=None)
    parser.add_argument('--rate', type=int, default=None)
    parser.add_argument('--prf', type=int, default=None)
    parser.add_argument('--psr', type=int, default=None)
    parser.add_argument('--pwr', type=str, default=None)
    parser.add_argument('remote', type=str, nargs='+')
    
    args = parser.parse_args()

    pr.DEBUG = args.debug
    cfg.print_frames = (args.debug > 0)
    
    cfg.blink_count = args.count

    if args.interval is not None:
        cfg.blink_max = args.interval
        cfg.blink_min = args.interval
    if args.max_interval is not None:
        cfg.blink_max = args.max_interval
    if args.min_interval is not None:
        cfg.blink_min = args.min_interval

    if cfg.blink_min > cfg.blink_max:
        cfg.blink_max = cfg.blink_min
    
    cfg.port = args.port
    
    cfg.if_name  = args.interface
    cfg.if_bind  = (cfg.if_name, 0)

    addrs = netifaces.ifaddresses(cfg.if_name).get(netifaces.AF_PACKET)
    cfg.if_eui64 = addrs[0]['addr'].replace(':','')
    cfg.if_addr = bytes.fromhex(cfg.if_eui64)

    WPANFrame.set_ifaddr(cfg.if_addr, 0xffff)

    if args.channel is not None:
        cfg.dw1000_channel = args.channel
    if args.pcode is not None:
        cfg.dw1000_pcode = args.pcode
    if args.rate is not None:
        cfg.dw1000_rate = args.rate
    if args.prf is not None:
        cfg.dw1000_prf = args.prf
    if args.psr is not None:
        cfg.dw1000_txpsr = args.psr
    if args.profile is not None:
        cfg.dw1000_profile = args.profile

    cfg.remotes = {}
    
    for host in args.remote:
        addr = socket.getaddrinfo(host, cfg.port, socket.AF_INET6)[0][4]
        pipe = UDPTailPipe()
        pipe.connect(addr)
        cfg.remotes[host] = pipe
        
    pr.debug('Tail transmitter starting...')
    
    SetDWAttr('channel', cfg.dw1000_channel)
    SetDWAttr('pcode', cfg.dw1000_pcode)
    SetDWAttr('prf', cfg.dw1000_prf)
    SetDWAttr('rate', cfg.dw1000_rate)
    SetDWAttr('txpsr', cfg.dw1000_txpsr)

    if cfg.dw1000_profile is not None:
        SetDWAttr('profile', cfg.dw1000_profile)
                    
    filt = GetDWAttr('frame_filter')
    SetDWAttr('frame_filter', 0)

    SocketLoop()

    SetDWAttr('frame_filter', filt)

if __name__ == "__main__": main()

