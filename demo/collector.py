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

LISTEN_PORT = 12345
MAX_RECV_LEN = 4096
INTERVAL = 0.1

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def collected(tag, anchors):
    logger.info('tag %s at %s', tag,
                ', '.join('%s:%#x' % (x, anchors[x]) for x in sorted(anchors)))

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
