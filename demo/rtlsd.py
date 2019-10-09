#!/usr/bin/python3
#
# Tail example server
#

import os
import sys
import time
import sched
import random
import threading
import json
import socket
import select
import logging
import argparse
import configparser
import traceback

import numpy as np

from tail import *
from tdoa import *
from dwarf import *

from numpy import dot
from numpy.linalg import LinAlgError


class cfg():

    debug = 0

    config_json   = '/etc/tail.json'

    server_addr   = ''
    server_port   = 8913
    client_port   = 9475
    
    tag_beacon_timer      = 0.010
    tag_ranging_timer     = 0.010
    tag_timeout_timer     = 0.050
    
    anchor_wakeup_timer   = (None,None)
    anchor_request_timer  = 0.010
    anchor_response_timer = 0.010
    anchor_ranging_timer  = 0.010
    anchor_timeout_timer  = 0.050
    
    max_dist      = 25.0
    max_ddoa      = 25.0
    max_change    = 5.0
    
    filter_len    = 100
    
    force_ref     = None

    sleep_min     = 0.0005

CONFIG_FILE = '/etc/tail.conf'


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def dprint(level, *args, **kwargs):
    if cfg.debug >= level:
        print(*args, file=sys.stderr, flush=True, **kwargs)


def woodoo(T):
    dprint(4, 'woodoo: {}'.format(T))
    T41 = T[3] - T[0]
    T32 = T[2] - T[1]
    T54 = T[4] - T[3]
    T63 = T[5] - T[2]
    T51 = T[4] - T[0]
    T62 = T[5] - T[1]
    ToF = 2 * (T41*T63 - T32*T54) / (T51+T62)
    DoF = (ToF / DW1000_CLOCK_HZ) * Cabs
    return DoF


class Timeout():

    def __init__(self, timer, delay, func, args):
        self.timer   = timer
        self.expiry  = 0
        self.delay   = delay
        self.func    = func
        self.args    = args
        self.armed   = False
        self.expired = False

    def expire(self):
        if self.armed:
            self.armed   = False
            self.expired = True
            try:
                self.func(*self.args)
            except Exception as err:
                dprint(3, 'EXCEPTION in Timeout::expire: {}: {}'.format(err.__class__.__name__,err))

    def arm(self, delay=None):
        if not self.armed:
            if delay is None:
                delay = self.delay
            self.armed   = True
            self.expired = False
            self.expiry  = time.time() + delay
            self.timer.arm(self)

    def unarm(self):
        if self.armed:
            self.timer.unarm(self)
            self.armed   = False
            self.expired = False
            self.expiry  = 0


class Timer(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.lock = threading.Condition()
        self.list = {}
        self.start()

    def arm(self,timeout):
        self.lock.acquire()
        self.list[timeout.expiry] = timeout
        self.lock.notify_all()
        self.lock.release()

    def unarm(self,timeout):
        self.lock.acquire()
        if timeout.expiry in self.list:
            self.list.pop(timeout.expiry)
            self.lock.notify_all()
        self.lock.release()

    def run(self):
        self.running = True
        self.lock.acquire()
        while self.running:
            if self.list:
                next = min(self.list)
                sleep = next - time.time()
                if sleep < cfg.sleep_min:
                    tout = self.list[next]
                    self.list.pop(next)
                    tout.expire()
                else:
                    self.lock.wait(sleep / 2)
            else:
                self.lock.wait(1)
        self.lock.release()

    def stop(self):
        self.lock.acquire()
        self.running = False
        self.lock.notify_all()
        self.lock.release()


class GeoFilter():

    def __init__(self, zero, lenght):
        self.zero = zero
        self.lenght = lenght
        self.reset()

    def reset(self):
        self.val_filt = self.zero.copy()
        self.count = 0
        
    def update(self,value):
        self.count += 1
        flen = min(self.count, self.lenght)
        diff = value - self.val_filt
        self.val_filt += diff / flen

    def avg(self):
        return self.val_filt.copy()


class TRX():

    def __init__(self,origin,anchor,frame,tinfo):
        self.origin = origin
        self.anchor = anchor
        self.key    = anchor.key
        self.frame  = frame
        self.tinfo  = tinfo
        self.ts     = tinfo['rawts']

    def get_ref_level(self):
        if self.anchor.refok:
            return self.get_rx_level()
        else:
            return -150

    def get_rx_level(self):
        POW = self.tinfo['cir_pwr']
        RXP = self.tinfo['rxpacc']
        if POW>0 and RXP>0:
            power = (POW << 17) / (RXP*RXP)
            level = RxPower2dBm(power)
            return level
        else:
            return -120

    def get_fp_level(self):
        FP1 = self.tinfo['fp_ampl1']
        FP2 = self.tinfo['fp_ampl2']
        FP3 = self.tinfo['fp_ampl3']
        RXP = self.tinfo['rxpacc']
        if FP1>0 and FP2>0 and FP3>0 and RXP>0:
            power = (FP1*FP1 + FP2*FP2 + FP3*FP3) / (RXP*RXP)
            level = RxPower2dBm(power)
            return level
        else:
            return -120

    def get_noise(self):
        N = self.tinfo['noise']
        return N

    def get_xtal_ratio(self):
        I = self.tinfo['ttcki']
        O = self.tinfo['ttcko']
        return O/I


class Tag():

    def __init__(self,server,eui,name,colour):
        self.key = bytes.fromhex(eui)
        self.eui = eui
        self.name = name
        self.server = server
        self.beacon = None
        self.common = None
        self.coord = np.zeros(3)
        self.cfilt = GeoFilter(np.zeros(3), cfg.filter_len)
        self.blinks = None
        self.ranging = False
        self.beacon_timer = Timeout(server.timer, cfg.tag_beacon_timer, Tag.beacon_expire, (self,))
        self.ranging_timer = Timeout(server.timer, cfg.tag_ranging_timer, Tag.ranging_expire, (self,))
        self.timeout_timer = Timeout(server.timer, cfg.tag_timeout_timer, Tag.timeout_expire, (self,))

    def start_ranging(self):
        self.beacon_timer.arm()
        self.timeout_timer.arm()
        self.ranging_start = time.time()
        self.blinks = ( {}, {}, {} )
        self.ranging = True

    def finish_ranging(self):
        self.beacon_timer.unarm()
        self.ranging_timer.unarm()
        self.timeout_timer.unarm()
        self.ranging = False

    def distance_to(self, obj):
        return dist(self.coord, obj.coord)

    def distance_avg_to(self, obj):
        return dist(self.cfilt.avg(), obj.coord)

    def update_coord(self, npcoord):
        self.cfilt.update(npcoord)
        if dist(self.cfilt.avg(), npcoord) < cfg.max_change:
            self.coord = npcoord

    def get_coord_avg(self):
        return self.cfilt.avg()

    def hyperlater(ref, alist):
        B0 = np.array(ref.coord)
        B  = np.array([A.coord for A in alist])
        R  = np.array([alist[A][0] for A in alist])
        S  = np.array([alist[A][1] for A in alist])
        dprint(4, 'Tag::hyperlater:\n{}\n{}\n{}\n{}'.format(B0,B,R,S))
        (X,N) = hyperlater(B0,B,R,S)
        return X
        
    def laterate(self):
        try:
            ref = self.ref
            rkey = self.ref.key
            anchors = {}
            T = [ 0, 0, 0, 0, 0, 0 ]
            for (akey,anchor) in self.server.anchor_keys.items():
                if akey != rkey:
                    try:
                        T[0] = self.blinks[0][akey].ts
                        T[1] = self.blinks[0][rkey].ts
                        T[2] = self.blinks[1][rkey].ts
                        T[3] = self.blinks[1][akey].ts
                        T[4] = self.blinks[2][akey].ts
                        T[5] = self.blinks[2][rkey].ts
                        L = woodoo(T)
                        R = ref.distance_to(anchor)
                        D = R - L
                        if -cfg.max_ddoa < D < cfg.max_ddoa:
                            anchors[anchor] = (D,1.0)
                            dprint(2, ' * Anchor: {} {:.1f}dBm LAT:{:.3f} REF:{:.3f} DOA:{:.3f}'.format(anchor.eui,self.blinks[0][akey].get_rx_level(),L,R,D))
                        else:
                            dprint(2, ' * Anchor: {} {:.3f} BAD TDOA'.format(anchor.eui,D))
                    except KeyError:
                        dprint(2, '  * Anchor: {} NOT FOUND'.format(anchor.eui))
                    except ZeroDivisionError:
                        dprint(2, '  * Anchor: {} BAD TIMES'.format(anchor.eui))
            coord = Tag.hyperlater(ref,anchors)
            self.update_coord(coord)
            self.update_stats(ref, anchors)
            self.server.send_client_msg(Type='TAG', Tag=self.eui, Coord=self.coord.tolist())
            dprint(1, 'Tag::laterate: LAT:{} AVG:{}'.format(coord, self.get_coord_avg()))
                
        except (KeyError,ValueError,AttributeError,LinAlgError) as err:
            eprint('Tag::laterate failed: {}: {}'.format(err.__class__.__name__, err))

    
    def update_stats(self, ref, anchors):
        for anchor in anchors:
            ref_dist = self.distance_avg_to(ref)
            anc_dist = self.distance_avg_to(anchor)
            loc_ddoa = ref_dist - anc_dist
            lat_ddoa = anchors[anchor][0]
            err_ddoa = lat_ddoa - loc_ddoa
            err_tick = (err_ddoa / Cabs) * DW1000_CLOCK_HZ
            msg  = 'Tag::update_stats: '
            msg += 'REF:{} '.format(ref.eui)
            msg += 'ANC:{} '.format(anchor.eui)
            msg += 'ref_dist:{:.3f} '.format(ref_dist)
            msg += 'anc_dist:{:.3f} '.format(anc_dist)
            msg += 'loc_ddoa:{:.3f} '.format(loc_ddoa)
            msg += 'lat_ddoa:{:.3f} '.format(lat_ddoa)
            msg += 'err_ddoa:{:.3f} '.format(err_ddoa)
            dprint(3, msg)

    def select_ref(self):
        if cfg.force_ref:
            self.ref = self.server.get_anchor(cfg.force_ref)
            self.ref.register_tag(self)
            dprint(2, 'Tag::select_ref: Tag:{} => Anchor:{}'.format(self.eui, self.ref.eui))
            return
        if True:
            N = len(self.server.anchor_refs)
            I = random.randrange(0,N)
            self.ref = list(self.server.anchor_refs.values())[I]
            self.ref.register_tag(self)
            dprint(2, 'Tag::select_ref: Tag:{} => Anchor:{}'.format(self.eui, self.ref.eui))
            return
        if self.blinks[0]:
            rxl = { trx:trx.get_ref_level() for trx in self.blinks[0].values() }
            trx = max(rxl, key=rxl.get)
            if trx.anchor.ref:
                self.ref = trx.anchor
                self.ref.register_tag(self)
                dprint(2, 'Tag::select_ref: Tag:{} => Anchor:{} {:.1f}dBm'.format(trx.origin.eui, trx.anchor.eui, trx.get_ref_level()))
    
    def beacon_expire(self):
        dprint(3, 'Tag::beacon_expire @ {}'.format(time.time() - self.ranging_start))
        if self.ref:
            self.ref.transmit_beacon(self.eui)

    def ranging_expire(self):
        dprint(3, 'Tag::ranging_expire @ {}'.format(time.time() - self.ranging_start))
        self.laterate()
        self.select_ref()
        self.finish_ranging()

    def timeout_expire(self):
        dprint(3, 'Tag::timeout_expire @ {}'.format(time.time() - self.ranging_start))
        self.select_ref()
        self.finish_ranging()
        
    def add_blink(self,trx):
        dprint(4, 'Tag::add_blink:   ANC:{} Rx:{:.1f}dBm'.format(trx.anchor.eui, trx.get_rx_level()))
        if not self.ranging:
            self.start_ranging()
        self.blinks[0][trx.key] = trx

    def add_beacon(self,trx):
        if self.ranging:
            tag = trx.origin.eui
            anc = trx.anchor.eui
            src = trx.frame.get_src_eui()
            if src == trx.origin.ref.eui:
                dprint(4, 'Tag::add_beacon:  ANC:{} SRC:{} Rx:{:.1f}dBm'.format(anc, src, trx.get_rx_level()))
                self.blinks[1][trx.key] = trx
                self.beacon_timer.unarm()

    def add_ranging(self,trx):
        if self.ranging:
            dprint(4, 'Tag::add_ranging: ANC:{} Rx:{:.1f}dBm'.format(trx.anchor.eui, trx.get_rx_level()))
            self.blinks[2][trx.key] = trx
            self.ranging_timer.arm()


class Anchor():

    def __init__(self, server, name, eui, host, port, coord, ref, antd=0.0):
        self.server  = server
        self.sock    = server.sock
        self.name    = name
        self.host    = host
        self.port    = port
        self.eui     = eui
        self.refok   = ref
        self.coord   = np.array(coord)
        self.antdo   = antd
        self.raddr   = socket.getaddrinfo(host, port, socket.AF_INET6)[0][4]
        self.key     = self.raddr[0]
        self.ranging_start  = None
        self.ranging_iter   = None
        self.ranging_peer   = None
        self.ranging_blinks = None
        self.wakeup_timer   = Timeout(server.timer, cfg.anchor_wakeup_timer[0], Anchor.wakeup_expire, (self,))
        self.request_timer  = Timeout(server.timer, cfg.anchor_request_timer, Anchor.request_expire, (self,))
        self.response_timer = Timeout(server.timer, cfg.anchor_response_timer, Anchor.response_expire, (self,))
        self.ranging_timer  = Timeout(server.timer, cfg.anchor_ranging_timer, Anchor.ranging_expire, (self,))
        self.timeout_timer  = Timeout(server.timer, cfg.anchor_timeout_timer, Anchor.timeout_expire, (self,))

        if cfg.anchor_wakeup_timer[0]:
            self.wakeup_timer.arm()

    def distance_to(self, obj):
        return dist(self.coord, obj.coord)

    def offset(self):
        return int(self.antdo)

    def set_offset(self, offset):
        self.antdo = offset
        dprint(3, 'set_offset: {} {:.3f}'.format(self.eui, offset))

    def adjust_offset(self, adjust):
        self.antdo -= adjust
        dprint(3, 'offset: {} {:+.3f} {:.3f}'.format(self.eui, adjust, self.antdo))

    def sendmsg(self, **args):
        data = json.dumps(args)
        dprint(3, 'Anchor::sendmsg {}'.format(data))
        self.sock.sendto(data.encode(), self.raddr)

    def register_tag(self, tag):
        self.sendmsg(Type='REGISTER', Tag=tag.eui)

    def remove_tag(self,tag):
        self.sendmsg(Type='REMOVE', Tag=tag.eui)

    def transmit_beacon(self, ref, sub=0, dst=0xffff, flags=0):
        frame = TailFrame()
        frame.set_src_addr(self.eui)
        frame.set_dst_addr(dst)
        frame.tail_protocol = 1
        frame.tail_frmtype = 1
        frame.tail_subtype = sub
        frame.tail_flags = flags
        frame.tail_beacon = bytes.fromhex(ref)
        self.sendmsg(Type='FRAME', Data=frame.encode().hex())

    def start_ranging_with(self, anchor):
        dprint(3, 'Anchor::start_ranging_with: {} <> {}'.format(self.eui,anchor.eui))
        self.ranging_peer = anchor
        self.ranging_start = time.time()
        self.ranging_blinks = ( {}, {}, {} )
        self.timeout_timer.arm()
        self.request_timer.arm()
        self.transmit_beacon(self.eui, sub=1, dst=self.ranging_peer.eui)

    def finish_ranging(self):
        self.timeout_timer.unarm()
        self.request_timer.unarm()
        self.response_timer.unarm()
        self.ranging_peer = None
        self.ranging_blinks = None

    def two_way_ranging(self):
        try:
            T = [ 0, 0, 0, 0, 0, 0 ]
            T[0] = self.ranging_blinks[0][self.key].ts + self.offset()
            T[1] = self.ranging_blinks[0][self.ranging_peer.key].ts - self.ranging_peer.offset()
            T[2] = self.ranging_blinks[1][self.ranging_peer.key].ts + self.ranging_peer.offset()
            T[3] = self.ranging_blinks[1][self.key].ts - self.offset()
            T[4] = self.ranging_blinks[2][self.key].ts + self.offset()
            T[5] = self.ranging_blinks[2][self.ranging_peer.key].ts - self.ranging_peer.offset()
            D = woodoo(T)
            self.server.add_anchor_twr(self, self.ranging_peer, D)
        
        except (KeyError,ValueError,AttributeError,LinAlgError) as err:
            dprint(3, 'Anchor::TWR failed: {}: {}'.format(err.__class__.__name__, err))

    def wakeup_expire(self):
        dprint(3, 'Anchor::wakeup_expire')
        self.wakeup_timer.arm(random.uniform(cfg.anchor_wakeup_timer[0], cfg.anchor_wakeup_timer[1]))
        try:
            key = next(self.ranging_iter)
            anchor = self.server.get_anchor(key)
            if anchor is not self:
                self.start_ranging_with(anchor)
        except (StopIteration,TypeError) as err:
            self.ranging_iter = iter(self.server.anchor_keys)

    def timeout_expire(self):
        dprint(3, 'Anchor::timeout_expire @ {}'.format(time.time() - self.ranging_start))
        self.finish_ranging()
        
    def request_expire(self):
        dprint(3, 'Anchor::request_expire @ {}'.format(time.time() - self.ranging_start))
        if self.ranging_peer:
            self.ranging_peer.transmit_beacon(self.eui, sub=2, dst=self.eui)
            self.response_timer.arm()

    def response_expire(self):
        dprint(3, 'Anchor::response_expire @ {}'.format(time.time() - self.ranging_start))
        if self.ranging_peer:
            self.transmit_beacon(self.eui, sub=3, dst=self.ranging_peer.eui)
            self.ranging_timer.arm()

    def ranging_expire(self):
        dprint(3, 'Anchor::ranging_expire @ {}'.format(time.time() - self.ranging_start))
        if self.ranging_peer:
            self.two_way_ranging()
            self.finish_ranging()

    def add_beacon(self,trx,sub):
        dprint(4, 'Anchor::add_beacon[{}]: {} Rx:{:.1f}dBm'.format(sub, trx.anchor.eui, trx.get_rx_level()))
        if self.ranging_peer:
            self.ranging_blinks[sub][trx.key] = trx
        

class Client():

    def __init__(self, pipe):
        self.pipe = pipe
        self.key  = self.pipe.remote[0]
        self.fd   = self.pipe.sock.fileno()

    def sendmsg(self, **args):
        data = json.dumps(args)
        dprint(3, 'Client::sendmsg {}'.format(data))
        self.pipe.sendmsg(data)

    def recvmsg(self):
        while self.pipe.hasmsg():
            msg = self.pipe.getmsg()
            dprint(1, 'Client::recvmsg: {}'.format(msg))

        
class Server():

    def __init__(self, addr=cfg.server_addr, port=cfg.server_port):
        self.laddr = (addr,port,0,0)
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.laddr)
        self.sockets = select.poll()
        self.sockets.register(self.sock, select.POLLIN)
        self.clients = {}
        self.cliefds = {}
        self.tags = {}
        self.anchor_refs = {}
        self.anchor_keys = {}
        self.anchor_euis = {}
        self.anchor_twrs = {}
        self.timer = Timer()

    def stop(self):
        self.timer.stop()

    def add_client(self, client):
        self.clients[client.key] = client
        self.cliefds[client.fd] = client
        self.sockets.register(client.pipe.sock, select.POLLIN)
        dprint(4, 'Server::add_client {}'.format(client.key))

    def rem_client(self, client):
        dprint(4, 'Server::rem_client {}'.format(client.key))
        self.clients.pop(client.key)
        self.cliefds.pop(client.fd)
        self.sockets.unregister(client.pipe.sock)
        
    def add_anchor(self, args):
        dprint(4, 'Server::add_anchor {}'.format(args))
        anchor = Anchor(self, **args)
        self.anchor_keys[anchor.key] = anchor
        self.anchor_euis[anchor.eui] = anchor
        if anchor.refok:
            self.anchor_refs[anchor.key] = anchor

    def rem_anchor(self, anchor):
        dprint(4, 'Server::rem_anchor {}'.format(anchor.key))
        self.anchor_keys.pop(anchor.key, None)
        self.anchor_euis.pop(anchor.eui, None)
        self.anchor_refs.pop(anchor.key, None)

    def get_anchor(self, key):
        if key in self.anchor_keys:
            return self.anchor_keys[key]
        elif key in self.anchor_euis:
            return self.anchor_euis[key]
        raise KeyError

    def get_anchor_twr(self, anchor_a, anchor_b):
        key = (anchor_a,anchor_b)
        dis = anchor_a.distance_to(anchor_b)
        twr = dis
        if key in self.anchor_twrs:
            twr = self.anchor_twrs[key].avg()
        return twr

    def add_anchor_twr(self, anchor_a, anchor_b, dist):
        if -cfg.max_dist < dist < cfg.max_dist:
            key1 = (anchor_a,anchor_b)
            key2 = (anchor_b,anchor_a)
            if key1 not in self.anchor_twrs:
                filt = GeoFilter(0.0, cfg.filter_len)
                self.anchor_twrs[key1] = filt
                self.anchor_twrs[key2] = filt
            self.anchor_twrs[key1].update(dist)
            avg = self.anchor_twrs[key1].avg()
            dprint(3, 'add_anchor_twr: {}<>{} DIS:{:.3f} AVG:{:.3f}'.format(anchor_a.eui, anchor_b.eui, dist, avg))

    def add_tag(self, args):
        dprint(4, 'Server::add_tag {}'.format(args))
        tag = Tag(self,**args)
        self.tags[tag.eui] = tag
        self.tags[tag.key] = tag
        
    def rem_tag(self, tag):
        dprint(4, 'Server::rem_tag {}'.format(tag.key))
        self.tags.pop(tag.eui, None)
        self.tags.pop(tag.key, None)
        
    def get_tag(self, key):
        return self.tags[key]

    def send_client_msg(self, **args):
        for key in list(self.clients):
            client = self.clients[key]
            try:
                client.sendmsg(**args)
            except ConnectionError:
                self.rem_client(client)

    def recv_anchor_frame(self,anchor,msg):
        #dprint(4, 'Server::recv_anchor_frame MSG:{}'.format(msg))
        tinfo = msg['TSInfo']
        frame = TailFrame(bytes.fromhex(msg['Frame']))
        if frame.tail_frmtype == 0:
            src = msg['Src']
            tag = self.get_tag(src)
            tag.add_blink(TRX(tag,anchor,frame,tinfo))
        elif frame.tail_frmtype == 3:
            src = msg['Src']
            tag = self.get_tag(src)
            tag.add_ranging(TRX(tag,anchor,frame,tinfo))
        elif frame.tail_frmtype == 1:
            ref = frame.tail_beacon.hex()
            if frame.tail_subtype == 0:
                tag = self.get_tag(ref)
                tag.add_beacon(TRX(tag,anchor,frame,tinfo))
            elif frame.tail_subtype == 1:
                anc = self.get_anchor(ref)
                anc.add_beacon(TRX(anc,anchor,frame,tinfo), 0)
            elif frame.tail_subtype == 2:
                anc = self.get_anchor(ref)
                anc.add_beacon(TRX(anc,anchor,frame,tinfo), 1)
            elif frame.tail_subtype == 3:
                anc = self.get_anchor(ref)
                anc.add_beacon(TRX(anc,anchor,frame,tinfo), 2)
                
    def recv_anchor_msg(self):
        try:
            (data,addr) = self.sock.recvfrom(4096)
            if addr[0] in self.anchor_keys:
                anchor = self.anchor_keys[addr[0]]
                msg = json.loads(data.decode())
                if msg['Type'] in ('RX','TX'):
                    self.recv_anchor_frame(anchor,msg)
                else:
                    raise ValueError
            else:
                eprint('Unknown anchor: {}'.format(addr[0]))
                
        except Exception as err:
            eprint('Unable to decode anchor message: {}\n*** {}: {}'.format(data.decode(), type(err).__name__, err))

            
    def socket_loop(self):

        tpipe = TCPTailPipe()
        tpipe.listen(('', cfg.client_port, 0, 0))
    
        self.sockets.register(tpipe.sock, select.POLLIN)

        while True:
            for (fd,flags) in self.sockets.poll(1000):
                try:
                    if flags & select.POLLIN:
                        if fd == self.sock.fileno():
                            self.recv_anchor_msg()
                        elif fd == tpipe.sock.fileno():
                            self.add_client(Client(tpipe.accept()))
                        elif fd in self.cliefds:
                            self.cliefds[fd].recvmsg()
                        
                except (KeyError,ValueError) as err:
                    eprint('{}: {}'.format(err.__class__.__name__, err))
        
        socks.unregister(tpipe.sock)


def main():

    if False: ##os.path.exists(CONFIG_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            for key,val in config['server'].items():
                setattr(cfg,key,val)
        except Exception as err:
            eprint('Could not read config file {}: {}'.format(CONFIG_FILE, err))
    
    parser = argparse.ArgumentParser(description="Tail Location server")
    
    parser.add_argument('-D', '--debug', action='count', default=cfg.debug)
    parser.add_argument('-c', '--config', type=str, default=cfg.config_json)
    parser.add_argument('--force_ref', type=str, default=None)
    
    args = parser.parse_args()
    
    cfg.debug = args.debug
    WPANFrame.verbosity = max((0, cfg.debug - 1))

    cfg.config_json = args.config

    server = Server()

    with open(cfg.config_json, 'r') as f:
        cfg.config = json.load(f)
    
    for arg in cfg.config.get('ANCHORS'):
        server.add_anchor(arg)

    for arg in cfg.config.get('TAGS'):
        server.add_tag(arg)

    if args.force_ref:
        for (key,anchor) in server.anchor_keys.items():
            if anchor.name == args.force_ref:
                cfg.force_ref = key
    
    try:
        server.socket_loop()

    except KeyboardInterrupt:
        server.stop()
    

if __name__ == "__main__": main()

