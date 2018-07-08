#!/usr/bin/python3
#
# Test hack for developing RPi Tail algorithms
#

import argparse
import ipaddress
import netifaces
import socket
import select
import ctypes
import json


class Config():
    remote     = None
    rpc_port   = 61666
    rpc_addr   = None
    rpc_dest   = None
    rpc_bind   = None

cfg = Config()



def SendRPC(sock,func,args):
    data = {
        'func': func,
        'args': args,
    }
    msg = json.dumps(data)
    sock.sendto(msg.encode(), cfg.rpc_dest)


def SocketLoop():
    rsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rsock.bind(cfg.rpc_bind)
    
    SendRPC(rsock, 'blink', 0)

    
def main():
    global cfg
    
    parser = argparse.ArgumentParser(description="Anchor daemon")
    
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('remote', type=str, help="Remote address")
    
    args = parser.parse_args()

    addr = socket.getaddrinfo(args.remote, args.port, socket.AF_INET)[0][4]
    
    cfg.rpc_addr = addr[0]
    cfg.rpc_port = addr[1]
    cfg.rpc_dest = addr
    cfg.rpc_bind = ('', cfg.rpc_port)

    print('Connecting to anchor {}'.format(cfg.rpc_addr))

    SocketLoop()
    


if __name__ == "__main__":
    main()

