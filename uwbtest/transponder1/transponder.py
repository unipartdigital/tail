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
    dw1000_power    = 0x85858585
    dw1000_smart    = 0

    if_name         = 'wpan0'

    data_file       = None

    port            = 61777

    
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
    frame.set_dst_addr(0xffff)
    frame.tail_protocol = 1
    frame.tail_frmtype = 1
    frame.tail_subtype = 0
    frame.tail_flags = 0
    frame.tail_beacon = bid
    data = frame.encode()
    rsock.send(data)


class rxThread(threading.Thread):
    
    def __init__(self,rsock):
        threading.Thread.__init__(self)
        self.running = False
        self.rsock = rsock
        
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
                except Exception as err:
                    pr.error('{}: {}'.format(type(err).__name__, err))
        
    def stop(self):
        self.running = False

    def recv_time(self):
        (data,ancl,_,_) = self.rsock.recvmsg(4096, 1024, socket.MSG_ERRQUEUE)
        frame = TailFrame(data,ancl)
        if frame.tail_protocol == 1 and frame.tail_frmtype == 1:
            frame.timestamp.tsinfo.cir_pwr = cfg.dw1000_power
            ExportData(frame)
            if cfg.print_frames:
                print(frame)

    def recv_frame(self):
        (data,ancl,_,rem) = self.rsock.recvmsg(4096, 1024, 0)
        frame = TailFrame(data,ancl)
        if frame.tail_protocol == 1 and frame.tail_frmtype == 1:
            ExportData(frame)
            if cfg.print_frames:
                print(frame)


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
    
    rx = rxThread(rsock)
    rx.start()

    pipe = UDPTailPipe()
    pipe.listen(cfg.bind)
    
    try:
        while True:
            try:
                while True:
                    msg = json.loads(pipe.recvmsg())
                    pr.debug('JSON: {}'.format(msg))
                    cmd = msg.get('CMD', 'None')
                    if cmd == 'beacon':
                        id = msg.get('ID', 0)
                        SendBeacon(rsock, id)
                    elif cmd == 'exit':
                        raise SystemExit
                    
            except ConnectionError:
                pass
        
    except KeyboardInterrupt:
        pr.error('Exiting...')

    rx.stop()
    rsock.close()


def main():

    parser = argparse.ArgumentParser(description="Tag emulator")

    parser.add_argument('-D', '--debug', action='count', default=0)
    parser.add_argument('-C', '--csv', type=str, default=None)
    parser.add_argument('-I', '--interface', type=str, default=cfg.if_name)
    parser.add_argument('-i', '--interval', type=float, help='ignored')
    parser.add_argument('-M', '--max-interval', type=float, help='ignored')
    parser.add_argument('-N', '--min-interval', type=float, help='ignored')
    parser.add_argument('-n', '--count', type=int, help='ignored')
    parser.add_argument('-p', '--port', type=int, default=cfg.port)
    parser.add_argument('--profile', type=str, default=None)
    parser.add_argument('--channel', type=int, default=None)
    parser.add_argument('--pcode', type=int, default=None)
    parser.add_argument('--rate', type=int, default=None)
    parser.add_argument('--prf', type=int, default=None)
    parser.add_argument('--psr', type=int, default=None)
    parser.add_argument('--pwr', type=str, default=None)
    parser.add_argument('remote', type=str, nargs='*', help='ignored')
    
    args = parser.parse_args()

    pr.DEBUG = args.debug
    cfg.print_frames = (args.debug > 1)

    cfg.port = args.port
    cfg.bind = ('', cfg.port, 0, 0)
    
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
    if args.pwr is not None:
        cfg.dw1000_power = args.pwr
    if args.profile is not None:
        cfg.dw1000_profile = args.profile

    if args.csv is not None:
        cfg.data_file = open(args.csv,'w')

    pr.debug('Tail transponder starting...')
    pr.debug('  profile   : {}'.format(cfg.dw1000_profile))
    pr.debug('  channel   : {}'.format(cfg.dw1000_channel))
    pr.debug('  pcode     : {}'.format(cfg.dw1000_pcode))
    pr.debug('  rate      : {}'.format(cfg.dw1000_rate))
    pr.debug('  prf       : {}'.format(cfg.dw1000_prf))
    pr.debug('  psr       : {}'.format(cfg.dw1000_txpsr))
    pr.debug('  power     : {:08x}'.format(cfg.dw1000_power))
    
    SetDWAttr('channel', cfg.dw1000_channel)
    SetDWAttr('pcode', cfg.dw1000_pcode)
    SetDWAttr('prf', cfg.dw1000_prf)
    SetDWAttr('rate', cfg.dw1000_rate)
    SetDWAttr('txpsr', cfg.dw1000_txpsr)
    SetDWAttr('smart_power', cfg.dw1000_smart)
    SetDWAttr('tx_power', cfg.dw1000_power)

    if cfg.dw1000_profile is not None:
        SetDWAttr('profile', cfg.dw1000_profile)
    
    SocketLoop()


if __name__ == "__main__": main()

