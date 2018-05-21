#!/usr/bin/python3

# This is a very quick and dirty proof of concept to collect tag
# blinks and forward them to a central collection server.
#
# Do not, under any circumstances, use this code in anything even
# remotely resembling a production environment.

import argparse
import ctypes
import ipaddress
import json
import netifaces
import socket
import socketserver

LISTEN_PORT = 61616
SEND_PORT = 12345

for name, value in (('SO_TIMESTAMPING', 37),
                    ('SOF_TIMESTAMPING_RX_HARDWARE', (1 << 2)),
                    ('SOF_TIMESTAMPING_RAW_HARDWARE', (1 << 6))):
    if not hasattr(socket, name):
        setattr(socket, name, value)


class Timespec(ctypes.Structure):

    _fields_ = [("tv_sec", ctypes.c_long),
                ("tv_nsec", ctypes.c_long)]

    def __int__(self):
        return ((self.tv_sec * 1000000000 + self.tv_nsec) << 32)

    def __str__(self):
        return '%#x' % int(self)

    def __bool__(self):
        return bool(self.tv_sec or self.tv_nsec)


class Timehires(ctypes.Structure):

    _fields_ = [("tv_nsec", ctypes.c_uint64),
                ("tv_frac", ctypes.c_uint32),
                ("__res", ctypes.c_uint32)]

    def __int__(self):
        return ((self.tv_nsec << 32) | self.tv_frac)

    def __str__(self):
        return '%#x' % int(self)

    def __bool__(self):
        return bool(self.tv_nsec or self.tv_frac)



class Timestamp(ctypes.Structure):

    _fields_ = [("sw", Timespec),
                ("legacy", Timespec),
                ("hw", Timespec),
                ("hr", Timehires)]

    def __str__(self):
        return ','.join('%s=%s' % (x[0], getattr(self, x[0]))
                        for x in self._fields_
                        if getattr(self, x[0]))


class AnchorRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        (data, sock, ancdata, msg_flags) = self.request
        (host, port, flowinfo, scopeid) = self.client_address
        (addr, _, zone) = host.partition('%')
        values = {'anchor': anchor, 'data': data.hex()}
        ip = ipaddress.ip_address(addr)
        if ip.is_link_local:
            tag = bytearray(ip.packed[8:])
            tag[0] ^= 0x02
            values['tag'] = tag.hex()
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if (cmsg_level == socket.SOL_SOCKET and
                cmsg_type == socket.SO_TIMESTAMPING):
                ts_raw = cmsg_data.ljust(ctypes.sizeof(Timestamp), b'\0')
                ts = Timestamp.from_buffer_copy(ts_raw)
                values['ts'] = int(ts.hr if ts.hr else ts.hw)
        res = json.dumps(values)
        print(res)
        client.sendto(res.encode() + b'\n', (args.server, args.port))


class AnchorServer(socketserver.UDPServer):

    address_family = socket.AF_INET6
    allow_reuse_address = True
    max_ancdata_size = socketserver.UDPServer.max_packet_size

    def server_bind(self):
        super(AnchorServer, self).server_bind()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_TIMESTAMPING,
                               (socket.SOF_TIMESTAMPING_RX_HARDWARE |
                                socket.SOF_TIMESTAMPING_RAW_HARDWARE))

    def get_request(self):
        (data, ancdata, msg_flags, client_addr) = self.socket.recvmsg(
            self.max_packet_size, self.max_ancdata_size
        )
        return (data, self.socket, ancdata, msg_flags), client_addr


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anchor daemon")
    parser.add_argument('-i', '--interface', type=str, default='lowpan0',
                        help="Listening network interface")
    parser.add_argument('-l', '--listen', type=int, default=LISTEN_PORT,
                        help="Listening port")
    parser.add_argument('-p', '--port', type=int, default=SEND_PORT)
    parser.add_argument('server', type=str, help="Server address")
    args = parser.parse_args()
    ifaddrs = netifaces.ifaddresses(args.interface)
    anchor = ifaddrs.get(netifaces.AF_PACKET)[0]['addr'].replace(':', '')
    scope = socket.if_nametoindex(args.interface)
    server = AnchorServer(('', args.listen, 0, scope), AnchorRequestHandler)
    client = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    server.serve_forever(poll_interval=None)
