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

    config_json = 'config.json'

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

    jconfig = {}
    tags = {}

CONFIG_FILE = '/etc/tail.conf'


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

    def __init__(self, name, eui, colour, algo=None):
        self.eui = eui
        self.name = name
        self.colour = colour
        self.coord = np.ones(3) * -10
        self.cfilt = GeoFilter(np.zeros(3), cfg.coord_filter_len)
        self.bfilt = GeoFilter(np.zeros(3), cfg.bubble_filter_len)

    def plot(self, ax):
        self.p1 = ax.plot([], [], 'o', mfc=self.colour, ms=10)
        self.p2 = ax.plot([], [], 'o', mfc='#00008010', mec='#00000000', ms=1)
        self.p3 = ax.annotate('', (0,0))

    def update(self,X):
        self.cfilt.update(X)
        self.bfilt.update(X)
        self.coord = self.cfilt.avg()

    def draw(self):
        mean = self.bfilt.avg()
        mstd = self.bfilt.dev()
        mstd = min(mstd,5.0)
        ppl.setp(self.p1, xdata=self.coord[0])
        ppl.setp(self.p1, ydata=self.coord[1])
        ppl.setp(self.p2, xdata=mean[0])
        ppl.setp(self.p2, ydata=mean[1])
        ppl.setp(self.p2, ms=mstd*cfg.std_pixels)
        ppl.setp(self.p3, text='{0} ({1[0]:.2f},{1[1]:.2f},{1[2]:.2f})'.format(self.name,self.coord))
        ppl.setp(self.p3, position=(self.coord[0]+0.15,self.coord[1]+0.15))
        
        
class Room():

    def __init__(self):
        self.fig = ppl.figure()
        self.fig.set_size_inches(cfg.room_w)
        self.ax = self.fig.add_subplot(1,1,1)
        self.ax.set_title(cfg.title)
        self.ax.set_xlim(cfg.room_x)
        self.ax.set_ylim(cfg.room_y)
        
        for anchor in cfg.jconfig.get('ANCHORS'):
            name = anchor['name']
            self.ax.plot(anchor['coord'][0],anchor['coord'][1],'rx')
            self.ax.annotate(name, (anchor['coord'][0]-0.3,anchor['coord'][1]-0.3))

        for arg in cfg.jconfig.get("TAGS"):
            tag = Tag(**arg)
            tag.plot(self.ax)
            cfg.tags[tag.eui] = tag

        self.fig.show()
    
    def update(self):
        for eui in cfg.tags:
            cfg.tags[eui].draw()
        self.fig.canvas.draw()


class Receiver(threading.Thread):

    def __init__(self,host,port):
        threading.Thread.__init__(self)
        self.saddr = TCPTailPipe.get_saddr(host,port)

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
                        if msg['Type'] == 'TAG' and msg['Tag']:
                            eui = msg['Tag']
                            if eui in cfg.tags:
                                tag = cfg.tags[eui]
                                tag.update(msg['Coord'])
                                print('TAG:{0} COORD:{1[0]:.3f},{1[1]:.3f},{1[2]:.3f}'.format(msg['Tag'],msg['Coord']))

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

    if False: ##os.path.exists(CONFIG_FILE):
        try:
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            for key,val in config['client'].items():
                setattr(cfg,key,val)
        except Exception as err:
            eprint('Could not read config file {}: {}'.format(CONFIG_FILE, err))
    
    parser = argparse.ArgumentParser(description="Tail 3D client example")
    
    parser.add_argument('-s', '--server', type=str, default=cfg.server_host)
    parser.add_argument('-p', '--port', type=int, default=cfg.server_port)
    parser.add_argument('-f', '--filter', type=int, default=cfg.coord_filter_len)
    parser.add_argument('-c', '--config', type=str, default=cfg.config_json)
    
    args = parser.parse_args()

    cfg.coord_filter_len = args.filter
    
    cfg.server_port  = args.port
    cfg.server_host  = args.server
    cfg.config_json  = args.config

    if cfg.config_json:
        with open(cfg.config_json, 'r') as f:
            cfg.jconfig = json.load(f)

    room = Room()
    recv = Receiver(cfg.server_host, cfg.server_port)
            
    try:
        recv.start()
        while True:
            room.update()

    except KeyboardInterrupt:
        eprint('Exiting...')

    recv.stop()

if __name__ == "__main__": main()

