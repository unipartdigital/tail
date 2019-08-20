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


class cfg():

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
    
    quiet           = 0
    promisc         = False
    print_frames    = True

    blink_dst       = 'ffff'
    blink_size      = 64
    blink_delay     = None
    blink_count     = None
    

def SendBlink(rsock):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(cfg.blink_dst)
    frame.tail_payload = b'\xbb' * cfg.blink_size
    rsock.send(frame.encode())

def RecvTime(rsock):
    (data,ancl,_,_) = rsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
    frame = TailFrame(data,ancl)
    if cfg.print_frames:
        print(frame)

def RecvBlink(rsock):
    (data,ancl,_,rem) = rsock.recvmsg(4096, 1024, 0)
    frame = TailFrame(data,ancl)
    if cfg.print_frames:
        print(frame)
    

class txThread(threading.Thread):
    def __init__(self,rsock):
        threading.Thread.__init__(self)
        self.rsock = rsock;
        self.running = False
        self.count = 0
        
    def run(self):
        if cfg.blink_delay:
            self.running = True
            while self.running:
                SendBlink(self.rsock);
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
            for (fd,flags) in socks.poll(1000):
                try:
                    if fd == self.rsock.fileno():
                        if flags & select.POLLIN:
                            RecvBlink(self.rsock)
                        if flags & select.POLLERR:
                            RecvTime(self.rsock)
                        self.count += 1
                except Exception as err:
                    pr.error('{}: {}'.format(type(err).__name__, err))

    def stop(self):
        self.running = False


def SocketLoop():

    rsock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.PROTO_IEEE802154)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                     socket.SOF_TIMESTAMPING_RX_HARDWARE |
                     socket.SOF_TIMESTAMPING_TX_HARDWARE |
                     socket.SOF_TIMESTAMPING_RAW_HARDWARE |
                     socket.SOF_TIMESTAMPING_TX_SOFTWARE |
                     socket.SOF_TIMESTAMPING_RX_SOFTWARE |
                     socket.SOF_TIMESTAMPING_SOFTWARE)
    rsock.bind(cfg.if_bind)

    tx = txThread(rsock)
    rx = rxThread(rsock)
    
    tx.start()
    rx.start()
    
    try:
        while True:
            if cfg.quiet == 1:
                print('*** TX:{} RX:{}'.format(tx.count, rx.count))
            time.sleep(1)
    
    except KeyboardInterrupt:
        print('Exiting...')

    tx.stop()
    rx.stop()
    
    rsock.close()


def main():

    parser = argparse.ArgumentParser(description="uTrack Connector daemon")

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-I', '--interface', type=str, default=cfg.if_name)
    parser.add_argument('-P', '--promiscuous-mode', action='store_true', default=False)
    parser.add_argument('-s', '--size', type=int, default=cfg.blink_size)
    parser.add_argument('-c', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('-i', '--interval', type=float, default=cfg.blink_delay)
    parser.add_argument('-q', '--quiet', action='count', default=0)
    parser.add_argument('--dest', type=str, default=cfg.blink_dst)
    parser.add_argument('--channel', type=int, default=None)
    parser.add_argument('--pcode', type=int, default=None)
    parser.add_argument('--prf', type=int, default=None)
    parser.add_argument('--psr', type=int, default=None)
    parser.add_argument('--txpsr', type=int, default=None)
    parser.add_argument('--pwr', type=str, default=None)
    parser.add_argument('--txpwr', type=str, default=None)
    parser.add_argument('--smart', type=bool, default=None)
    parser.add_argument('--rate', type=int, default=None)
    
    args = parser.parse_args()

    pr.DEBUG = args.debug

    cfg.quiet = args.quiet
    cfg.promisc = args.promiscuous_mode
    cfg.print_frames = (args.quiet == 0)
    
    cfg.blink_dst = bytes.fromhex(args.dest)
    cfg.blink_size = args.size
    cfg.blink_count = args.count
    cfg.blink_delay = args.interval
    
    cfg.if_name  = args.interface
    cfg.if_bind  = (cfg.if_name, 0)

    addrs = netifaces.ifaddresses(cfg.if_name).get(netifaces.AF_PACKET)
    cfg.if_eui64 = addrs[0]['addr'].replace(':','')
    cfg.if_addr = bytes.fromhex(cfg.if_eui64)

    WPANFrame.set_ifaddr(cfg.if_addr, b'\xff\xff')
    
    if args.channel is not None:
        cfg.dw1000_channel = args.channel
    if args.pcode is not None:
        cfg.dw1000_pcode = args.pcode
    if args.prf is not None:
        cfg.dw1000_prf = args.prf
    if args.psr is not None:
        cfg.dw1000_txpsr = args.psr
    if args.txpsr is not None:
        cfg.dw1000_txpsr = args.txpsr
    if args.pwr is not None:
        cfg.dw1000_power = args.pwr
    if args.txpwr is not None:
        cfg.dw1000_power = args.txpwr
    if args.smart is not None:
        cfg.dw1000_smart = args.smart
    if args.rate is not None:
        cfg.dw1000_rate = args.rate

    if cfg.quiet == 0:
        print('UWB dump starting...')
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

    filt = GetDWAttr('frame_filter')
    
    if cfg.promisc:
        SetDWAttr('frame_filter', 0)
    
    SocketLoop()
    
    if cfg.promisc:
        SetDWAttr('frame_filter', filt)


if __name__ == "__main__": main()

