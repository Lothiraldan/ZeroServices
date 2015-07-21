# -*- coding: utf-8 -*-
import asyncio
import aiozmq
import time
import zmq
import sys
import json
import logging
import socket

from asyncio import coroutine
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM, IPPROTO_UDP, SOL_SOCKET, SO_REUSEADDR, IPPROTO_IP, IP_MULTICAST_TTL, IP_ADD_MEMBERSHIP, inet_aton
from os.path import join
from os import makedirs
from asyncio import coroutine

from zeroservices.medium import BaseMedium

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()


class ServerProtocol(object):

    def __init__(self, callback, loop):
        self.callback = callback
        self.loop = loop

    def connection_made(self, transport):
        self.transport = transport

    def msg_received(self, msg):
        sender, message_type, message = msg
        message_type = message_type.decode('utf-8')
        message = json.loads(message.decode('utf-8'))

        asyncio.async(self.callback(message_type, message, sender=sender), loop=self.loop)


class SubProtocol(object):

    def __init__(self, callback, loop):
        self.callback = callback
        self.loop = loop

    def connection_made(self, transport):
        self.transport = transport

    def msg_received(self, msg):
        event_type, event_data = msg[0].decode('utf-8').split(' ', maxsplit=1)
        event_data = json.loads(event_data)

        asyncio.async(self.callback(event_type, event_data), loop=self.loop)


class ZeroMQMedium(BaseMedium):

    @asyncio.coroutine
    def start(self):

        # Pub
        self.pub = yield from aiozmq.create_zmq_stream(
            zmq.PUB,
            bind="tcp://*:*",
            loop=self.loop
        )

        # Server
        self.server, self.server_t = yield from aiozmq.create_zmq_connection(
            lambda: ServerProtocol(self.process_message, self.loop),
            zmq.ROUTER, bind="tcp://*:*",
            loop=self.loop
        )
        self.server_t.transport.setsockopt(zmq.IDENTITY, self.node_id.encode('utf-8'))

        # Sub
        self.sub, _ = yield from aiozmq.create_zmq_connection(
            lambda: SubProtocol(self.process_event, self.loop),
            zmq.SUB,
            loop=self.loop
        )

        yield from super(ZeroMQMedium, self).start()

    def close(self):
        self.server.close()
        self.pub.close()
        self.sub.close()
        super(ZeroMQMedium, self).close()

    def get_node_info(self):
        node_info = super(ZeroMQMedium, self).get_node_info()

        node_info['server_port'] = int(tuple(self.server.bindings())[0].split(':')[-1])
        node_info['pub_port'] = int(tuple(self.pub._transport.bindings())[0].split(':')[-1])

        return node_info

    def connect_to_node(self, node_id):
        peer_info = self.directory[node_id]
        peer_address = 'tcp://%s:%s' % (peer_info['address'],
                                        peer_info['pub_port'])
        self.logger.debug('Connecting my sub socket to %s' % peer_address)
        self.sub.connect(peer_address)
        self.sub.setsockopt(zmq.SUBSCRIBE, ''.encode('utf-8'))

    @coroutine
    def send(self, node_id, message, message_type="message", wait_response=True):
        peer_info = self.directory[node_id]

        address = peer_info['address']
        port = peer_info['server_port']

        address = 'tcp://%(address)s:%(port)s' % locals()
        request_socket = yield from aiozmq.create_zmq_stream(
            zmq.DEALER, connect=address, loop=self.loop
        )

        log_info = (message_type, json.dumps(message), address)
        self.logger.info('Send %s/%s to %s' % log_info)
        message = (message_type.encode('utf-8'), json.dumps(message).encode('utf-8'))
        request_socket.write(message)

        if wait_response:
            message_type, message = yield from request_socket.read()
            assert message_type.decode('utf-8') == 'message'
            return json.loads(message.decode('utf-8'))

        yield from request_socket.drain()
        request_socket.close()

    @coroutine
    def publish(self, event_type, event_data):
        self.logger.debug("Publish %s %s" % (event_type, event_data))
        pub_message = '%s %s' % (event_type, json.dumps(event_data))
        pub_message = (pub_message.encode('utf-8'),)
        self.pub.write(pub_message)

        return

    @asyncio.coroutine
    def respond(self, sender, message, message_type="message"):
        data = (sender, message_type.encode('utf-8'), json.dumps(message).encode('utf-8'))
        self.server.write(data)

    def send_registration_answer(self, node_id, node_info=None):
        node_info = self.get_node_info()

        # Find my local address
        peer_info = self.directory[node_id]
        s = socket.socket(AF_INET, SOCK_STREAM)
        s.connect((peer_info['address'], peer_info['server_port']))
        node_info['address'] = s.getsockname()[0]
        s.close()

        return super(ZeroMQMedium, self).send_registration_answer(node_id, node_info)

    @asyncio.coroutine
    def add_server_entrypoint(self, path=None):
        if path is not None:
            # Ensure path exists
            try:
                makedirs(path)
            except OSError:
                # Path exists
                pass

            socket_path = 'ipc://%s' % join(path, 'server.sock')
            server, _ = yield from aiozmq.create_zmq_connection(
                lambda: ServerProtocol(self.process_message, self.loop),
                zmq.ROUTER, bind=socket_path,
                loop=self.loop
            )
            self.server_sockets.add(server)
            print("Server", server)

            return socket_path, server
