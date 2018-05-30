#!/usr/bin/python3

# This is a very quick and dirty proof of concept to collect tag blink
# reports.
#
# Do not, under any circumstances, use this code in anything even
# remotely resembling a production environment.

import argparse
import json
import logging
import socket
import selectors
import time
import tdoa
import numpy as np

LISTEN_PORT = 12345
MAX_RECV_LEN = 4096
INTERVAL = 0.1

CAIR = 299700000

ANCHORS = {
    '70b3d5b1e0000005': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e0000006': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e0000007': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e0000008': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e0000009': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e000000a': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e000000b': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e000000c': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e000000d': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e000000e': { 'pos': (1,1,1), 'sigma': 0.10, },
    '70b3d5b1e000000f': { 'pos': (1,1,1), 'sigma': 0.10, },
}


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def collected(tag, anchors):
    B = np.array([ANCHORS[a]['pos'] for a in anchors])
    S = np.array([ANCHORS[a]['sigma'] for a in anchors])
    R = np.array([anchors[a] for a in anchors])
    R = ((R - np.amin(R)) / 4294967296E9) * CAIR
    if R.size > 5:
        X,C = tdoa.hyperlater(B,R,S)
        print('Tag {0} location {1}'.format(tag,X))
    else:
        print('Tag {0} lateration fail'.format(tag))


def server(port):
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
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
