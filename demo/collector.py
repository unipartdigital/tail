#!/usr/bin/python3
#
# This is a very quick and dirty proof of concept to collect tag blink
# reports.
#
# Do not, under any circumstances, use this code in anything even
# remotely resembling a production environment.
#

import argparse
import json
import logging
import socket
import selectors
import time
import tdoa
import numpy as np
import matplotlib.pyplot as plt

LISTEN_PORT = 12345
MAX_RECV_LEN = 4096
INTERVAL = 0.01

SIGMA = 1.0E-9
EWMA = 25
CAIR = 299700000

ROOM = ((-0.5,9.0),(-0.5,6.0))

ANCHORS = {
    '70b3d5b1e0000006': { 'ID': 'BSS1', 'pos': (0.00,0.00,0.00), 'sigma': SIGMA, },
    '70b3d5b1e000000a': { 'ID': 'BSS2', 'pos': (0.00,5.36,0.00), 'sigma': SIGMA, },
    '70b3d5b1e0000005': { 'ID': 'BSS3', 'pos': (8.35,0.00,0.00), 'sigma': SIGMA, },
    '70b3d5b1e000000c': { 'ID': 'BSS4', 'pos': (8.35,5.45,0.00), 'sigma': SIGMA, },
    '70b3d5b1e000000e': { 'ID': 'BSS5', 'pos': (2.80,2.75,1.75), 'sigma': SIGMA, },
    '70b3d5b1e0000007': { 'ID': 'BSS6', 'pos': (5.63,2.75,1.75), 'sigma': SIGMA, },
}

TAGS = {
    '70b3d5b1e000000d': { 'ID': 'TAG1', 'CNT': 1, 'Xavg': np.array((0,0,0)), 'Vavg': 0.0, },
    '70b3d5b1e0000001': { 'ID': 'TAG2', 'CNT': 1, 'Xavg': np.array((0,0,0)), 'Vavg': 0.0, },
    '70b3d5b1e000000b': { 'ID': 'TAG3', 'CNT': 1, 'Xavg': np.array((0,0,0)), 'Vavg': 0.0, },
    '70b3d5b1e0000103': { 'ID': 'ringtail', 'CNT': 1, 'Xavg': np.array((0,0,0)), 'Vavg': 0.0, },
    '70b3d5b1e0000104': { 'ID': 'brushtail', 'CNT': 1, 'Xavg': np.array((0,0,0)), 'Vavg': 0.0, },
}


## Visualisation

fig = plt.figure()
ax1 = fig.add_subplot(1,1,1)

fig.set_size_inches(16,10)

ax1.set_title('Tag Location')
ax1.set_xlim(ROOM[0])
ax1.set_ylim(ROOM[1])

for ID in ANCHORS:
    ax1.plot(ANCHORS[ID]['pos'][0],ANCHORS[ID]['pos'][1],'rx')

p1 = ax1.plot([], [], 'o', mfc='#0000C0FF')
p2 = ax1.plot([], [], 'o', mfc='#00008010', mec='#00000000', ms=1)
p3 = ax1.annotate('', (0,0))

fig.show()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def visualise(T,X,C,D):
    if D>4: D=4
    plt.setp(p1, xdata=X[0])
    plt.setp(p1, ydata=X[1])
    plt.setp(p2, xdata=C[0])
    plt.setp(p2, ydata=C[1])
    plt.setp(p2, ms=D*300)
    plt.setp(p3, text='{0} ({1[0]:.3f},{1[1]:.3f},{1[2]:.3f})'.format(T,C))
    plt.setp(p3, position=(C[0]+D,C[1]+D))
    fig.canvas.draw()


def collected(tag, anchors):
    global TAGS
    keys = sorted(anchors.keys())
    name = TAGS[tag]['ID']
    B = np.array([ANCHORS[a]['pos'] for a in keys])
    S = np.array([ANCHORS[a]['sigma'] for a in keys])
    R = [anchors[a] for a in keys]
    R = np.array([x - min(R) for x in R])
    R = (R / 4294967296E9) * CAIR
    S = S * CAIR
    print('Tag {0} R={1}'.format(name,R))
    try:
        X,C = tdoa.hyperlater(B,R,S)
        if np.amin(X) > -1 and np.amax(X) < 10:
            Xavg = TAGS[tag]['Xavg']
            Vavg = TAGS[tag]['Vavg']
            ewma = TAGS[tag]['CNT']
            ewma = min(ewma,EWMA)
            Xdif = X-Xavg
            Xavg = Xavg + Xdif/ewma
            Vavg = Vavg + (tdoa.dsq(Xdif) - Vavg)/ewma
            Davg = np.sqrt(Vavg)
            TAGS[tag]['Xavg'] = Xavg
            TAGS[tag]['Vavg'] = Vavg
            TAGS[tag]['CNT'] += 1
            visualise(name,X,Xavg,Davg)
            print('Tag {0} location: {1} error est: {2:.3f}'.format(name,X,Davg))
            
    except np.linalg.LinAlgError as err:
        print('Tag {0} lateration fail: {1}'.format(name,err))


def server(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))
    sock.setblocking(False)
    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_READ)

    pending = {}
    while True:
        ready = sel.select(INTERVAL if pending else None)
        now = time.clock_gettime(time.CLOCK_MONOTONIC)
        if ready:
            raw = sock.recv(MAX_RECV_LEN)
            data = json.loads(raw)
            logger.debug(data)
            anchor = data.get('anchor', None)
            tag = data.get('tag', None)
            ts = data.get('ts', None)
            if anchor and tag and ts:
                if tag in pending:
                    pending[tag]['anchors'][anchor] = ts
                else:
                    pending[tag] = {
                        'expiry': (now + INTERVAL),
                        'anchors': {anchor: ts},
                    }
        expired = [tag for tag in pending if pending[tag]['expiry'] < now]
        for tag in expired:
            collected(tag, pending[tag]['anchors'])
            del pending[tag]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collector daemon")
    parser.add_argument('-l', '--listen', type=int, default=LISTEN_PORT,
                        help="Listening port")
    args = parser.parse_args()
    server(args.listen)
