#!/usr/bin/python3
#
# Tail example (server) client
#

import sys
import time
import socket
import select
import json
import argparse
import threading

from tail import *

import numpy as np
import matplotlib.pyplot as ppl


class cfg():

    server_host = 'resistor.qs.unipart.io'
    server_port = 9475

    title = 'Tail Demo Room'

    std_pixels = 150
    
    room_s = 1.25
    room_x = (-1, 10)
    room_y = (-2, 7)
    room_w = (room_s * (room_x[1] - room_x[0]), room_s * (room_y[1] - room_y[0]))

    coord_filter_len = 3
    bubble_filter_len  = 10

    config_json = 'config.json'

    tags = {}


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class GeoFilter():

    def __init__(self, zero, lenght):
        self.zero = zero
        self.lenght = lenght
        self.reset()

    def reset(self):
        self.val_filt = self.zero.copy()
        self.var_filt = 0.0
        self.count = 0
        
    def update(self,value):
        self.count += 1
        flen = min(self.count, self.lenght)
        diff = value - self.val_filt
        self.val_filt += diff / flen
        self.var_filt += (np.sum(diff*diff) - self.var_filt) / flen
        
    def avg(self):
        return self.val_filt.copy()

    def var(self):
        return self.var_filt.copy()

    def dev(self):
        return np.sqrt(self.var_filt)


class Tag():

    def __init__(self, room, eui):
        self.eui = eui
        self.name = None
        self.colour = None
        self.coord = np.ones(3) * -10
        self.cfilt = GeoFilter(np.zeros(3), cfg.coord_filter_len)
        self.bfilt = GeoFilter(np.zeros(3), cfg.bubble_filter_len)
        self.p1 = room.ax.plot([], [], 'o', ms=10)
        self.p2 = room.ax.plot([], [], 'o', mfc='#00008010', mec='#00000000', ms=1)
        self.p3 = room.ax.annotate('', (0,0))

    def update(self, name, coord, colour):
        self.cfilt.update(coord)
        self.bfilt.update(coord)
        self.coord = self.cfilt.avg()
        self.colour = colour
        self.name = name

    def redraw(self):
        mean = self.bfilt.avg()
        mstd = self.bfilt.dev()
        mstd = min(mstd,5.0)
        ppl.setp(self.p1, xdata=self.coord[0])
        ppl.setp(self.p1, ydata=self.coord[1])
        ppl.setp(self.p1, mfc=self.colour)
        ppl.setp(self.p2, xdata=mean[0])
        ppl.setp(self.p2, ydata=mean[1])
        ppl.setp(self.p2, ms=mstd*cfg.std_pixels)
        ppl.setp(self.p3, position=(self.coord[0]+0.15,self.coord[1]+0.15))
        if self.coord[2]:
            ppl.setp(self.p3, text='{0} ({1[0]:.2f},{1[1]:.2f},{1[2]:.2f})'.format(self.name,self.coord))
        else:
            ppl.setp(self.p3, text='{0} ({1[0]:.2f},{1[1]:.2f})'.format(self.name,self.coord))
        
        
class Room():

    def __init__(self):
        self.tags = {}
        self.fig = ppl.figure()
        self.fig.set_size_inches(cfg.room_w)
        self.ax = self.fig.add_subplot(1,1,1)
        self.ax.set_title(cfg.title)
        self.ax.set_xlim(cfg.room_x)
        self.ax.set_ylim(cfg.room_y)

        for anchor in cfg.config.get('ANCHORS'):
            name = anchor['name']
            self.ax.plot(anchor['coord'][0],anchor['coord'][1],'rx')
            self.ax.annotate(name, (anchor['coord'][0]-0.3,anchor['coord'][1]-0.3))

        self.fig.show()

    def update_tag(self, eui, name, coord, colour):
        if eui not in self.tags:
            self.tags[eui] = Tag(self,eui)
        self.tags[eui].update(name,coord,colour)
    
    def redraw(self):
        for tag in self.tags.values():
            tag.redraw()
        self.fig.canvas.draw()


class Receiver(threading.Thread):

    def __init__(self,room,host,port):
        threading.Thread.__init__(self)
        self.saddr = TCPTailPipe.get_saddr(host,port)
        self.room = room

    def run(self):
        Xcnt = 1
        Xavg = np.zeros(3)
        Vavg = np.zeros(1)
        
        tpipe = TCPTailPipe()
        
        self.running = True
        
        while self.running:
            try:
                tpipe.connect(self.saddr)
                while self.running:
                    try:
                        msg = json.loads(tpipe.recvmsg())
                        if msg['Type'] == 'TAG':
                            self.room.update_tag(msg['Tag'], msg['Name'], msg['Coord'], msg['Colour'])
                            print('TAG:{0} {1} {2} COORD:{3[0]:.3f},{3[1]:.3f},{3[2]:.3f}'.format(msg['Name'],msg['Tag'], msg['Colour'], msg['Coord']))

                    except (ValueError,KeyError,AttributeError) as err:
                        eprint('{}: {}'.format(err.__class__.__name__, err))
        
            except ConnectionError as err:
                eprint('{}: {}'.format(err.__class__.__name__, err))
                tpipe.close()
                time.sleep(1.0)

        tpipe.close()

    def stop(self):
        self.running = False
        

def main():

    parser = argparse.ArgumentParser(description="Tail 3D client example")
    
    parser.add_argument('-c', '--config', type=str, default=None)
    parser.add_argument('-s', '--server', type=str, default=None)
    parser.add_argument('-p', '--port', type=int, default=None)
    parser.add_argument('-f', '--filter', type=int, default=None)
    
    args = parser.parse_args()

    if args.config:
        cfg.config_json = args.config

    with open(cfg.config_json, 'r') as f:
        cfg.config = json.load(f)

    for (key,value) in cfg.config.get('DEMO').items():
        try:
            getattr(cfg,key)
            setattr(cfg,key,value)
        except AttributeError:
            eprint('Invalid DEMO config {}: {}'.format(key,value))

    if args.server:
        cfg.server_host = args.server
    if args.port:
        cfg.server_port = args.port
    if args.filter:
        cfg.coord_filter_len = args.filter
    
    room = Room()
    recv = Receiver(room, cfg.server_host, cfg.server_port)
            
    try:
        recv.start()
        while True:
            room.redraw()

    except KeyboardInterrupt:
        eprint('Exiting...')

    recv.stop()

if __name__ == "__main__": main()

