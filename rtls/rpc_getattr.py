#!/usr/bin/python3
#
# Test hack for developing RPi Tail algorithms
#

import pprint
import argparse
import ipaddress
import netifaces
import socket
import select
import ctypes
import json
import sys

class Config():
    remote     = None
    rpc_port   = 61666
    rpc_addr   = None
    rpc_dest   = None
    rpc_bind   = None

cfg = Config()



def RPCGetAttrRet(args):
    print('getAttr() = {}'.format(args))
    return True


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
        func = rpc.get('func', None)
        args = rpc.get('args', None)
        if func == 'getAttr::return':
            return RPCGetAttrRet(args)
    except:
        pass

    return False


def SocketLoop(attr):
    rsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rsock.bind(cfg.rpc_bind)
    
    SendRPC(rsock, 'getAttr', [attr])

    done = False
    
    while not done:
        rset,wset,eset = select.select([rsock],[],[])
        if rsock in rset:
            done = RecvRPC(rsock)

    
def main():
    global cfg
    
    parser = argparse.ArgumentParser(description="Anchor daemon")
    
    parser.add_argument('-p', '--port', type=int, default=cfg.rpc_port)
    parser.add_argument('remote', type=str, help="Remote address")
    parser.add_argument('attribute', type=str, help="DW1000 sysfs attribute")
    
    args = parser.parse_args()

    addr = socket.getaddrinfo(args.remote, args.port, socket.AF_INET)[0][4]

    attr = args.attribute
    
    cfg.rpc_addr = addr[0]
    cfg.rpc_port = addr[1]
    cfg.rpc_dest = addr
    cfg.rpc_bind = ('', cfg.rpc_port)

    SocketLoop(attr)
    


if __name__ == "__main__":
    main()

