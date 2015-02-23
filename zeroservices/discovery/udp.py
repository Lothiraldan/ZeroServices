import logging
import asyncio
import collections
import socket
import json
from copy import copy

from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM, IPPROTO_UDP, SOL_SOCKET, SO_REUSEADDR, IPPROTO_IP, IP_MULTICAST_TTL, IP_ADD_MEMBERSHIP, inet_aton
from asyncio import coroutine, futures

ANY = "0.0.0.0"
logger = logging.getLogger('UdpDiscoveryMedium')


@coroutine
def create_datagram_endpoint(self, protocol_factory,
                             local_addr=None, remote_addr=None, #*,
                             family=0, proto=0, flags=0):
    """Create datagram connection.
    Based on asyncio code with small fix"""
    if not (local_addr or remote_addr):
        if family == 0:
            raise ValueError('unexpected address family')
        addr_pairs_info = (((family, proto), (None, None)),)
    else:
        # join address by (family, protocol)
        addr_infos = collections.OrderedDict()
        for idx, addr in ((0, local_addr), (1, remote_addr)):
            if addr is not None:
                assert isinstance(addr, tuple) and len(addr) == 2, (
                    '2-tuple is expected')

                infos = yield from self.getaddrinfo(
                    *addr, family=family, type=socket.SOCK_DGRAM,
                    proto=proto, flags=flags)
                if not infos:
                    raise OSError('getaddrinfo() returned empty list')

                for fam, _, pro, _, address in infos:
                    key = (fam, pro)
                    if key not in addr_infos:
                        addr_infos[key] = [None, None]
                    addr_infos[key][idx] = address

        # each addr has to have info for each (family, proto) pair
        addr_pairs_info = [
            (key, addr_pair) for key, addr_pair in addr_infos.items()
            if not ((local_addr and addr_pair[0] is None) or
                    (remote_addr and addr_pair[1] is None))]

        if not addr_pairs_info:
            raise ValueError('can not get address information')

    exceptions = []

    for ((family, proto),
         (local_address, remote_address)) in addr_pairs_info:
        sock = None
        r_addr = None
        try:
            sock = socket.socket(
                family=family, type=socket.SOCK_DGRAM, proto=proto)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # FIX: Mandatory on Mac OS X
            if hasattr(socket, 'SO_REUSEPORT'):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.setblocking(False)

            if local_addr:
                sock.bind(local_address)
            if remote_addr:
                yield from self.sock_connect(sock, remote_address)
                r_addr = remote_address
        except OSError as exc:
            if sock is not None:
                sock.close()
            exceptions.append(exc)
        except:
            if sock is not None:
                sock.close()
            raise
        else:
            break
    else:
        raise exceptions[0]

    protocol = protocol_factory()
    waiter = futures.Future(loop=self)
    transport = self._make_datagram_transport(sock, protocol, r_addr,
                                              waiter)
    if self._debug:
        if local_addr:
            logger.info("Datagram endpoint local_addr=%r remote_addr=%r "
                        "created: (%r, %r)",
                        local_addr, remote_addr, transport, protocol)
        else:
            logger.debug("Datagram endpoint remote_addr=%r created: "
                         "(%r, %r)",
                         remote_addr, transport, protocol)
    yield from waiter
    return transport, protocol


@coroutine
def create_udp_multicast_endpoint(loop, address, port, protocol_factory,
                                  ttl=None):
    """ Create an udp multicast listening socket trough asyncio
    """
    transport, protocol = yield from create_datagram_endpoint(
        loop, lambda: protocol_factory,
        local_addr=(ANY, port), proto=IPPROTO_UDP)
    sock = transport.get_extra_info('socket')
    sock.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, 255)
    sock.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP,
                    inet_aton(address) + inet_aton(ANY))

    return transport, protocol


class UdpMulticastEmitterProtocol(object):

    def __init__(self, registration_address, registration_info, on_close):
        self.registration_address = registration_address
        self.registration_info = registration_info
        self.on_close = on_close

    def connection_made(self, transport):
        self.transport = transport
        # self.send_registration_infos()

    def send_registration_infos(self):
        self.transport.sendto(json.dumps(self.registration_info).encode('utf-8'),
                              self.registration_address)
        # loop.call_later(5, self.send_registration_infos)

    def connection_lost(self, exc):
        self.on_close.set_result(exc)


class UdpMulticastReceiverProtocol(object):

    def __init__(self, callback, loop, node_id, on_close):
        self.callback = callback
        self.loop = loop
        self.node_id = node_id
        self.on_close = on_close

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        decoded = json.loads(data.decode('utf-8'))
        if decoded['node_id'] == self.node_id:
            return
        decoded['address'] = addr[0]

        asyncio.async(self.callback('register', decoded), loop=self.loop)


class UdpDiscoveryMedium(object):

    MCAST_ADDR = "237.252.249.227"
    MCAST_PORT = 32000
    ANY = "0.0.0.0"

    def __init__(self, callback, loop, node_infos):
        self.callback = callback
        self.loop = loop
        self.node_id = node_infos['node_id']
        self.node_infos = copy(node_infos)

    @asyncio.coroutine
    def start(self):
        self.receiver_closed = asyncio.Future(loop=self.loop)
        self.receiver, _ = yield from create_udp_multicast_endpoint(
            self.loop, self.MCAST_ADDR, self.MCAST_PORT,
            UdpMulticastReceiverProtocol(self.callback, self.loop, self.node_id, self.receiver_closed),
            ttl=255)

        self.emitter_closed = asyncio.Future(loop=self.loop)
        self.emitter, self.emitter_t = yield from self.loop.create_datagram_endpoint(
            lambda: UdpMulticastEmitterProtocol((self.MCAST_ADDR, self.MCAST_PORT), self.node_infos, self.emitter_closed),
            local_addr=(self.ANY, 0),
            proto=IPPROTO_UDP
        )

    def close(self):
        self.receiver.close()
        self.emitter.close()

    @asyncio.coroutine
    def send_registration_infos(self):
        return self.emitter_t.send_registration_infos()

    def check_leak(self):
        return
