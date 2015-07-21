import asyncio
import collections
import socket
from json import dumps, loads
from copy import copy, deepcopy

from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM, IPPROTO_UDP, SOL_SOCKET, SO_REUSEADDR, IPPROTO_IP, IP_MULTICAST_TTL, IP_ADD_MEMBERSHIP, inet_aton
from asyncio import coroutine, futures


class MemoryDiscoveryMedium(object):

    MEDIUMS = set()

    def __init__(self, callback, loop, node_infos):
        self.callback = callback
        self.loop = loop
        self.node_id = node_infos['node_id']
        self.node_infos = deepcopy(node_infos)

    @classmethod
    def reset(cls):
        cls.MEDIUMS = set()

    @asyncio.coroutine
    def start(self):
        self.MEDIUMS.add(self)

    def close(self):
        if self in self.MEDIUMS:
            self.MEDIUMS.remove(self)

    def _receive_registration_infos(self, registrations_infos):
        registrations_infos = loads(registrations_infos)
        registrations_infos['address'] = '127.0.0.1'

        yield from self.callback('register', registrations_infos)

    @asyncio.coroutine
    def send_registration_infos(self):
        for medium in self.MEDIUMS:
            if medium is not self:
                yield from medium._receive_registration_infos(dumps(self.node_infos))

    @classmethod
    def check_leak(cls):
        if cls.MEDIUMS:
            mediums = cls.MEDIUMS
            cls.MEDIUMS = set()
            raise Exception(mediums)
