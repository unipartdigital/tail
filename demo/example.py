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


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, flush=True, **kwargs)


def msg_loop(host,port):

    saddr = TCPTailPipe.get_saddr(host, port)

    tpipe = TCPTailPipe()
    tpipe.connect(saddr)

    while True:
        try:
            msg = json.loads(tpipe.recvmsg())
            if msg['Type'] == 'TAG':
                print('{0} ({1[0]:.3f},{1[1]:.3f},{1[2]:.3f})'.format(msg['Tag'], msg['Coord']))

        except (ValueError,KeyError,AttributeError) as err:
            eprint('{}: {}'.format(err.__class__.__name__, err))
        
        except ConnectionError as err:
            eprint('{}: {}'.format(err.__class__.__name__, err))
            break
    
    tpipe.close()


def main():

    parser = argparse.ArgumentParser(description="Tail 3D client example")
    
    parser.add_argument('-p', '--port', type=int, default=9475)
    parser.add_argument('server', type=str, nargs='?', default='resistor.qs.unipart.io')
    
    args = parser.parse_args()
    
    msg_loop(args.server, args.port)
    

if __name__ == "__main__": main()

