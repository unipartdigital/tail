#!/usr/bin/python3
#
# Tail beacon
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

    dw1000_channel  = 3
    dw1000_pcode    = 9
    dw1000_prf      = 64
    dw1000_rate     = 850
    dw1000_txpsr    = 1024
    dw1000_power    = 0x4b4b4b4b
    dw1000_smart    = 0

    beacon_id       = 0
    
    if_name         = 'wpan0'

    blink_min       = 1.000  # [s]
    blink_max       = 1.000  # [s]
    blink_delay     = 0.001  # [s]
    blink_first     = 0.010  # [s]
    blink_dest      = 0xffff
    
    blink_count     = None
    blink_replies   = 0

    data_file       = None


def GetRxPower(CIRPWR, RXPACC):
    if RXPACC>0:
        Pwr = (CIRPWR << 17) / (RXPACC*RXPACC)
        Plog = 10*math.log10(Pwr)
        if cfg.dw1000_prf == 16:
            Plog -= 113.77
        else:
            Plog -= 121.74
        return Plog
    else:
        return 0

def GetFpPower(FPA1,FPA2,FPA3,RXPACC):
    if RXPACC>0:
        FPpwr = (FPA1*FPA1 + FPA2*FPA2 + FPA3*FPA3) / (RXPACC*RXPACC)
        FPlog = 10*math.log10(FPpwr)
        if cfg.dw1000_prf == 16:
            FPlog -= 113.77
        else:
            FPlog -= 121.74
        return FPlog
    else:
        return 0

def GetXTALRatio(ttcko,ttcki):
    if ttcko > 0 and ttcki > 0:
        return (ttcko / ttcki) * 1E6
    else:
        return 0


def ExportData(frame):
    if cfg.data_file is None:
        return
    eui = frame.if_addr.hex()
    bid = frame.tail_beacon
    tstamp = frame.timestamp
    tsinfo = frame.timestamp.tsinfo
    RxPower = GetRxPower(tsinfo.cir_pwr, tsinfo.rxpacc)
    FpPower = GetFpPower(tsinfo.fp_ampl1, tsinfo.fp_ampl2, tsinfo.fp_ampl2, tsinfo.rxpacc)
    XRatio = GetXTALRatio(tsinfo.ttcko, tsinfo.ttcki)
    line  = '0x{:08x}'.format(bid)		# 0
    line += ',{}'.format(eui)			# 1
    line += ',{}'.format(tstamp.sw)		# 2
    line += ',{}'.format(tstamp.hires)		# 3
    line += ',0x{:016x}'.format(tsinfo.rawts)	# 4
    line += ',{:.1f}'.format(RxPower)  		# 5
    line += ',{:.1f}'.format(FpPower)  		# 6
    line += ',{:.3f}'.format(XRatio)		# 7
    line += ',{}'.format(tsinfo.lqi)  		# 8
    line += ',{}'.format(tsinfo.snr)  		# 9
    line += ',{}'.format(tsinfo.fpr)  		# 10
    line += ',{}'.format(tsinfo.noise)  	# 11
    line += ',{}'.format(tsinfo.rxpacc)  	# 12
    line += ',{}'.format(tsinfo.fp_index)  	# 13
    line += ',{}'.format(tsinfo.fp_ampl1)  	# 14
    line += ',{}'.format(tsinfo.fp_ampl2)  	# 15
    line += ',{}'.format(tsinfo.fp_ampl3)  	# 16
    line += ',{}'.format(tsinfo.cir_pwr)  	# 17
    line += ',{}'.format(tsinfo.fp_pwr)  	# 18
    line += ',{}'.format(tsinfo.ttcko)  	# 19
    line += ',{}'.format(tsinfo.ttcki)  	# 20
    line += ',{:.2f}'.format(tsinfo.temp/100)  	# 21
    line += ',{:.3f}'.format(tsinfo.volt/1000) 	# 22
    line += '\n'
    cfg.data_file.write(line)
    cfg.data_file.flush()


def SendBeacon(rsock,bid):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(cfg.blink_dest)
    frame.tail_protocol = 1
    frame.tail_frmtype = 1
    frame.tail_subtype = 0
    frame.tail_flags = 0
    frame.tail_beacon = bid
    data = frame.encode()
    rsock.send(data)
    cfg.beacon_time = time.time()

    
def SendReply(rsock,bid):
    frame = TailFrame()
    frame.set_src_addr(cfg.if_addr)
    frame.set_dst_addr(cfg.blink_dest)
    frame.tail_protocol = 1
    frame.tail_frmtype = 1
    frame.tail_subtype = 0
    frame.tail_flags = 0x01
    frame.tail_beacon = (bid & ~0xf) | cfg.beacon_id
    data = frame.encode()
    rsock.send(data)


def RecvTime(rsock):
    (data,ancl,_,_) = rsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
    frame = TailFrame(data,ancl)
    if frame.tail_protocol == 1 and frame.tail_frmtype == 1:
        ExportData(frame)
        if cfg.print_frames:
            print(frame)

def RecvFrame(rsock):
    (data,ancl,_,rem) = rsock.recvmsg(4096, 1024, 0)
    frame = TailFrame(data,ancl)
    if frame.tail_protocol == 1 and frame.tail_frmtype == 1:
        ExportData(frame)
        if cfg.print_frames:
            print(frame)
        last_id = frame.tail_beacon & 0xf
        if last_id + 1 == cfg.beacon_id:
            if last_id == 0:
                time.sleep(cfg.blink_first)
            else:
                time.sleep(cfg.blink_delay)
            cfg.busy.acquire()
            SendReply(rsock,frame.tail_beacon)
            cfg.last_id = last_id
            cfg.busy.notify()
            cfg.busy.release()


class txThread(threading.Thread):
    def __init__(self,rsock):
        threading.Thread.__init__(self)
        self.rsock = rsock;
        self.running = False
        self.counter = 0
        
    def run(self):
        self.running = (cfg.beacon_id == 0)
        while self.running:
            try:
                self.counter += 1
                if cfg.blink_count:
                    if self.counter > cfg.blink_count:
                        self.running = False
                        break
                cfg.busy.acquire()
                cfg.last_id = 0
                SendBeacon(self.rsock, self.counter<<4)
                while cfg.last_id < cfg.blink_replies:
                    timeout = cfg.blink_max - (time.time() - cfg.beacon_time)
                    if timeout < 0.0001:
                        break
                    cfg.busy.wait(timeout/10)
                cfg.busy.release()
                timeout = cfg.blink_min - (time.time() - cfg.beacon_time)
                if timeout > 0.001:
                    time.sleep(timeout)
                
            except Exception as err:
                pr.error('{}: {}'.format(type(err).__name__, err))
    
    def stop(self):
        self.running = False


class rxThread(threading.Thread):
    def __init__(self,rsock):
        threading.Thread.__init__(self)
        self.rsock = rsock;
        self.running = False
        
    def run(self):
        self.running = True
        socks = select.poll()
        socks.register(self.rsock, select.POLLIN)
        while self.running:
            for (fd,flags) in socks.poll(100):
                try:
                    if fd == self.rsock.fileno():
                        if flags & select.POLLIN:
                            RecvFrame(self.rsock)
                        if flags & select.POLLERR:
                            RecvTime(self.rsock)
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
            time.sleep(1)
        
    except KeyboardInterrupt:
        pr.error('Exiting...')

    tx.stop()
    rx.stop()
    
    rsock.close()


def main():

    parser = argparse.ArgumentParser(description="Tag emulator")

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-C', '--csv', type=str, default=None)
    parser.add_argument('-I', '--interval', type=float, default=None)
    parser.add_argument('-M', '--max-interval', type=float, default=None)
    parser.add_argument('-N', '--min-interval', type=float, default=None)
    parser.add_argument('-d', '--delay', type=float, default=cfg.blink_delay)
    parser.add_argument('-f', '--first', type=float, default=cfg.blink_first)
    parser.add_argument('-B', '--beacon-id', type=int, default=cfg.beacon_id)
    parser.add_argument('-R', '--replies', type=int, default=0)
    parser.add_argument('-n', '--count', type=int, default=cfg.blink_count)
    parser.add_argument('--interface', type=str, default=cfg.if_name)
    parser.add_argument('--channel', type=int, default=None)
    parser.add_argument('--pcode', type=int, default=None)
    parser.add_argument('--prf', type=int, default=None)
    parser.add_argument('--psr', type=int, default=None)
    parser.add_argument('--pwr', type=str, default=None)
    
    args = parser.parse_args()

    pr.DEBUG = args.debug
    cfg.print_frames = (args.debug > 0)
    
    cfg.blink_count = args.count
    cfg.beacon_id = args.beacon_id

    if args.interval is not None:
        cfg.blink_max = args.interval
        cfg.blink_min = args.interval
    if args.max_interval is not None:
        cfg.blink_max = args.max_interval
    if args.min_interval is not None:
        cfg.blink_min = args.min_interval

    if cfg.blink_min > cfg.blink_max:
        cfg.blink_max = cfg.blink_min
    
    cfg.blink_delay = args.delay
    cfg.blink_first = args.first
    cfg.blink_replies = args.replies
    
    cfg.if_name  = args.interface
    cfg.if_bind  = (cfg.if_name, 0)

    addrs = netifaces.ifaddresses(cfg.if_name).get(netifaces.AF_PACKET)
    cfg.if_eui64 = addrs[0]['addr'].replace(':','')
    cfg.if_addr = bytes.fromhex(cfg.if_eui64)
    
    WPANFrame.set_ifaddr(cfg.if_addr, 0xffff)

    cfg.busy = threading.Condition()
    
    if args.channel is not None:
        cfg.dw1000_channel = args.channel
    if args.pcode is not None:
        cfg.dw1000_pcode = args.pcode
    if args.prf is not None:
        cfg.dw1000_prf = args.prf
    if args.psr is not None:
        cfg.dw1000_txpsr = args.psr
    if args.pwr is not None:
        cfg.dw1000_power = args.pwr

    if args.csv is not None:
        cfg.data_file = open(args.csv,'w')

    pr.debug('Tail transponder starting...')
    pr.debug('  channel   : {}'.format(cfg.dw1000_channel))
    pr.debug('  pcode     : {}'.format(cfg.dw1000_pcode))
    pr.debug('  prf       : {}'.format(cfg.dw1000_prf))
    pr.debug('  psr       : {}'.format(cfg.dw1000_txpsr))
    pr.debug('  rate      : {}'.format(cfg.dw1000_rate))
    pr.debug('  power     : {}'.format(cfg.dw1000_power))

    SetDWAttr('channel', cfg.dw1000_channel)
    SetDWAttr('pcode', cfg.dw1000_pcode)
    SetDWAttr('prf', cfg.dw1000_prf)
    SetDWAttr('rate', cfg.dw1000_rate)
    SetDWAttr('txpsr', cfg.dw1000_txpsr)
    SetDWAttr('smart_power', cfg.dw1000_smart)
    SetDWAttr('tx_power', cfg.dw1000_power)
    
    SocketLoop()


if __name__ == "__main__": main()

