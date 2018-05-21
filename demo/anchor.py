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

    def __str__(self):
        return '%ld.%09ld' % (self.tv_sec, self.tv_nsec)

    def __bool__(self):
        return bool(self.tv_sec or self.tv_nsec)


class Timestamp(ctypes.Structure):

    _fields_ = [("sw", Timespec),
                ("legacy", Timespec),
                ("hw", Timespec)]

    def __str__(self):
        return ','.join('%s=%s' % (x[0], getattr(self, x[0]))
                        for x in self._fields_
                        if getattr(self, x[0]))


class AnchorRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        (data, sock, ancdata, msg_flags) = self.request
        (host, port, flowinfo, scopeid) = self.client_address
        (addr, _, zone) = host.partition('%')
        values = {'data': data.hex()}
        ip = ipaddress.ip_address(addr)
        if ip.is_link_local:
            eui64 = bytearray(ip.packed[8:])
            eui64[0] ^= 0x02
            values['eui64'] = eui64.hex()
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if (cmsg_level == socket.SOL_SOCKET and
                cmsg_type == socket.SO_TIMESTAMPING):
                ts = Timestamp.from_buffer_copy(cmsg_data)
                values['ts'] = str(ts.hw)
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
    parser.add_argument('-l', '--listen', type=int, default=LISTEN_PORT,
                        help="Listening port")
    parser.add_argument('-p', '--port', type=int, default=SEND_PORT)
    parser.add_argument('server', type=str, help="Server address")
    args = parser.parse_args()
    server = AnchorServer(('', args.listen), AnchorRequestHandler)
    client = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    server.serve_forever(poll_interval=None)
