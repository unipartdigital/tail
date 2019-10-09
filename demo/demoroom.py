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
    
    filter_len = 10

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

    def __init__(self, name, eui, colour):
        self.eui = eui
        self.name = name
        self.colour = colour
        self.coord = None
        self.cfilt = GeoFilter(np.zeros(3), cfg.filter_len)

    def plot(self, ax):
        self.p1 = ax.plot([], [], 'o', mfc=self.colour, ms=10)
        self.p2 = ax.plot([], [], 'o', mfc='#00008010', mec='#00000000', ms=1)
        self.p3 = ax.annotate('', (0,0))

    def update(self, X):
        self.coord = X
        self.cfilt.update(X)
        Xavg = self.cfilt.avg()
        Rstd = self.cfilt.dev()
        Rstd = min(Rstd,10)
        ppl.setp(self.p1, xdata=self.coord[0])
        ppl.setp(self.p1, ydata=self.coord[1])
        ppl.setp(self.p2, xdata=Xavg[0])
        ppl.setp(self.p2, ydata=Xavg[1])
        ppl.setp(self.p2, ms=Rstd*cfg.std_pixels)
        ppl.setp(self.p3, text='{0} ({1[0]:.2f},{1[1]:.2f},{1[2]:.2f})'.format(self.name,Xavg))
        ppl.setp(self.p3, position=(Xavg[0]+Rstd,Xavg[1]+Rstd))
        
        
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
        self.fig.canvas.draw()


def msg_loop(host, port):

    saddr = socket.getaddrinfo(host, port, socket.AF_INET6)[0][4]

    tpipe = TCPTailPipe()

    room = Room()
    
    Xcnt = 1
    Xavg = np.zeros(3)
    Vavg = np.zeros(1)

    while True:
        try:
            tpipe.connect(saddr)

            while True:
                try:
                    msg = json.loads(tpipe.recvmsg())
                    
                    if msg['Type'] == 'TAG' and msg['Tag']:
                        eui = msg['Tag']
                        if eui in cfg.tags:
                            tag = cfg.tags[eui]
                            tag.update(msg['Coord'])
                            room.update()
                            print('TAG:{0} COORD:{1[0]:.3f},{1[1]:.3f},{1[2]:.3f}'.format(msg['Tag'],msg['Coord']))

                except (ValueError,KeyError,AttributeError) as err:
                    eprint('{}: {}'.format(err.__class__.__name__, err))
        
        except ConnectionError as err:
            eprint('{}: {}'.format(err.__class__.__name__, err))
            tpipe.close()
            time.sleep(1.0)

    tpipe.close()


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
    parser.add_argument('-c', '--config', type=str, default=cfg.config_json)
    
    args = parser.parse_args()

    cfg.server_port  = args.port
    cfg.server_host  = args.server
    cfg.config_json  = args.config

    if cfg.config_json:
        with open(cfg.config_json, 'r') as f:
            cfg.jconfig = json.load(f)

    msg_loop(cfg.server_host, cfg.server_port)
    

if __name__ == "__main__": main()

