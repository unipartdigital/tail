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


def RecvRPC(sock):
    (data, client) = sock.recvfrom(4096)
    try:
        rpc = json.loads(data.decode())
    except:
        rpc = { }
    print(rpc)
    
    
def SocketLoop():
    rsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rsock.bind(cfg.rpc_bind)

    while True:
        rset,wset,eset = [ rsock ], [ ], [ ]
        rset,wset,eset = select.select(rset,wset,eset)
        if rsock in rset:
            RecvRPC(rsock)

    
def main():
    global cfg
    
    parser = argparse.ArgumentParser(description="Anchor daemon")
    
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('remote', type=str, help="Remote address")
    
    args = parser.parse_args()

    cfg.rpc_addr = args.remote
    cfg.rpc_port = args.port
    cfg.rpc_dest = (cfg.rpc_addr, cfg.rpc_port)
    cfg.rpc_bind = ('', cfg.rpc_port)

    SocketLoop()
    


if __name__ == "__main__":
    main()

