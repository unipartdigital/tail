#!/usr/bin/python3

import sys
import time
import math
import json
import socket
import select
import argparse
import netifaces
import threading

from tail import *

from datetime import datetime


class cfg():

    dw1000_profile  = None
    dw1000_channel  = None
    dw1000_pcode    = None
    dw1000_prf      = None
    dw1000_rate     = None
    dw1000_txpsr    = None
    dw1000_power    = None
    dw1000_smart    = None

    if_name         = 'wpan0'
    if_addr         = None
    if_short        = None
    if_eui64        = None
    
    verbose         = 0
    promisc         = False

    blink_dst       = 'ffff'
    blink_delay     = None
    blink_count     = None



def SendBlink(rsock,bid):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(cfg.blink_dst)
    frame.tail_protocol = 1
    frame.tail_frmtype = 1
    frame.tail_subtype = 15
    frame.tail_flags = 0
    frame.tail_beacon = struct.pack('>Q', bid)
    rsock.send(frame.encode())


class txThread(threading.Thread):
    def __init__(self,rsock):
        threading.Thread.__init__(self)
        self.rsock = rsock;
        self.running = False
        self.count = 0
        
    def run(self):
        if cfg.blink_delay:
            self.running = True
            self.count = 1
            while self.running:
                SendBlink(self.rsock, self.count);
                time.sleep(cfg.blink_delay)
                self.count += 1
                if cfg.blink_count is not None:
                    if self.count > cfg.blink_count:
                        self.running = False
    
    def stop(self):
        self.running = False
 

class rxThread(threading.Thread):
    def __init__(self,rsock):
        threading.Thread.__init__(self)
        self.rsock = rsock;
        self.running = False
        self.count = 0
        
    def run(self):
        self.running = True
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
                        self.count += 1
                except Exception as err:
                    eprint('{}: {}'.format(err.__class__.__name__, err))

    def stop(self):
        self.running = False
        
    def recv_frame(self):
        (data,ancl,_,rem) = self.rsock.recvmsg(4096, 1024, 0)
        frame = TailFrame(data,ancl)
        print('*** {} RX {}'.format(datetime.now().time(), frame))

    def recv_time(self):
        (data,ancl,_,_) = self.rsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
        frame = TailFrame(data,ancl)
        print('*** {} TX {}'.format(datetime.now().time(), frame))


def SocketLoop():

    rsock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.PROTO_IEEE802154)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                     socket.SOF_TIMESTAMPING_RX_HARDWARE |
                     socket.SOF_TIMESTAMPING_TX_HARDWARE |
                     socket.SOF_TIMESTAMPING_RAW_HARDWARE)
    rsock.bind((cfg.if_name, 0))

    tx = txThread(rsock)
    rx = rxThread(rsock)
    
    tx.start()
    rx.start()

    try:
        while True:
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        eprint('Exiting...')

    tx.stop()
    rx.stop()
    
    rsock.close()


def main():

    parser = argparse.ArgumentParser(description="uTrack Connector daemon")

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-I', '--interface', type=str, default=cfg.if_name)
    parser.add_argument('-P', '--promiscuous-mode', action='store_true', default=False)
    parser.add_argument('-i', '--interval', type=float, default=cfg.blink_delay)
    parser.add_argument('-c', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('--dest', type=str, default=cfg.blink_dst)
    parser.add_argument('--profile', type=str, default=cfg.dw1000_profile)
    parser.add_argument('--channel', type=int, default=cfg.dw1000_channel)
    parser.add_argument('--pcode', type=int, default=cfg.dw1000_pcode)
    parser.add_argument('--prf', type=int, default=cfg.dw1000_prf)
    parser.add_argument('--rate', type=int, default=cfg.dw1000_rate)
    parser.add_argument('--txpsr', type=int, default=cfg.dw1000_txpsr)
    parser.add_argument('--power', type=str, default=cfg.dw1000_power)
    
    args = parser.parse_args()

    WPANFrame.verbosity = args.verbose
    
    cfg.blink_dst = bytes.fromhex(args.dest)
    cfg.blink_count = args.count
    cfg.blink_delay = args.interval
    
    cfg.promisc = args.promiscuous_mode
    
    cfg.if_name  = args.interface
    cfg.if_addr  = GetDTAttrRaw('decawave,eui64')
    cfg.if_eui64 = cfg.if_addr.hex()
    WPANFrame.set_ifaddr(cfg.if_addr)

    cfg.dw1000_profile = args.profile
    cfg.dw1000_channel = args.channel
    cfg.dw1000_pcode = args.pcode
    cfg.dw1000_prf = args.prf
    cfg.dw1000_txpsr = args.txpsr
    cfg.dw1000_power = args.power
    cfg.dw1000_rate = args.rate

    if cfg.dw1000_power is not None:
        cfg.dw1000_smart = bool(cfg.dw1000_power & 0xff000000)

    if args.verbose > 1:
        print('UWB dump starting...')
        print('  profile   : {}'.format(cfg.dw1000_profile))
        print('  channel   : {}'.format(cfg.dw1000_channel))
        print('  pcode     : {}'.format(cfg.dw1000_pcode))
        print('  prf       : {}'.format(cfg.dw1000_prf))
        print('  psr       : {}'.format(cfg.dw1000_txpsr))
        print('  rate      : {}'.format(cfg.dw1000_rate))
        print('  power     : {}'.format(cfg.dw1000_power))
        print('  smart     : {}'.format(cfg.dw1000_smart))

    if cfg.dw1000_channel is not None:
        SetDWAttr('channel', cfg.dw1000_channel)
    if cfg.dw1000_pcode is not None:
        SetDWAttr('pcode', cfg.dw1000_pcode)
    if cfg.dw1000_prf is not None:
        SetDWAttr('prf', cfg.dw1000_prf)
    if cfg.dw1000_rate is not None:
        SetDWAttr('rate', cfg.dw1000_rate)
    if cfg.dw1000_txpsr is not None:
        SetDWAttr('txpsr', cfg.dw1000_txpsr)
    if cfg.dw1000_smart is not None:
        SetDWAttr('smart_power', cfg.dw1000_smart)
    if cfg.dw1000_power is not None:
        SetDWAttr('tx_power', cfg.dw1000_power)
    if cfg.dw1000_profile is not None:
        SetDWAttr('profile', cfg.dw1000_profile)

    filt = GetDWAttr('frame_filter')
    
    if cfg.promisc:
        SetDWAttr('frame_filter', 0)
    
    SocketLoop()
    
    if cfg.promisc:
        SetDWAttr('frame_filter', filt)


if __name__ == "__main__": main()

