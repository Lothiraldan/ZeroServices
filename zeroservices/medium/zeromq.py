# -*- coding: utf-8 -*-
import sys
import zmq
import time
from zmq.eventloop import ioloop
ioloop.install()
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream
import json
import logging
import socket

from socket import gethostname, getaddrinfo, AF_INET, SOCK_STREAM, SOCK_DGRAM, IPPROTO_UDP, SOL_SOCKET, SO_REUSEADDR, IPPROTO_IP, IP_MULTICAST_TTL, IP_ADD_MEMBERSHIP, inet_aton
from tornado import gen
from os.path import join
from os import makedirs
from uuid import uuid4

from zeroservices.medium import BaseMedium

logging.basicConfig(level=logging.DEBUG)

# Come from excellent http://stefan.sofa-rockers.org/2012/02/01/designing-and-testing-pyzmq-applications-part-1/
def stream(context, sock_type, bind, addr=None, subscribe=None,
        random=False):
    """
    Creates a :class:`~zmq.eventloop.zmqstream.ZMQStream`.

    :param sock_type: The ØMQ socket type (e.g. ``zmq.REQ``)
    :param addr: Address to bind or connect to formatted as *host:port*,
            *(host, port)* or *host* (bind to random port).
            If *bind* is ``True``, *host* may be:

            - the wild-card ``*``, meaning all available interfaces,
            - the primary IPv4 address assigned to the interface, in its
              numeric representation or
            - the interface name as defined by the operating system.

            If *bind* is ``False``, *host* may be:

            - the DNS name of the peer or
            - the IPv4 address of the peer, in its numeric representation.

            If *addr* is just a host name without a port and *bind* is
            ``True``, the socket will be bound to a random port.
    :param bind: Binds to *addr* if ``True`` or tries to connect to it
            otherwise.
    :param callback: A callback for
            :meth:`~zmq.eventloop.zmqstream.ZMQStream.on_recv`, optional
    :param subscribe: Subscription pattern for *SUB* sockets, optional,
            defaults to ``b''``.
    :returns: A tuple containg the stream and the port number.

    """
    sock = context.socket(sock_type)

    # Bind/connect the socket
    if addr:
        if bind:
            if not random:
                sock.bind(addr)
            else:
                port = sock.bind_to_random_port(addr)
        else:
            sock.connect(addr)

    # Add a default subscription for SUB sockets
    if sock_type == zmq.SUB:
        if subscribe:
            sock.setsockopt(zmq.SUBSCRIBE, subscribe)
        else:
            sock.setsockopt(zmq.SUBSCRIBE, b'')

    if random:
        return sock, int(port)
    else:
        return sock


class ZeroMQMedium(BaseMedium):

    #Multicast registration
    ANY = "0.0.0.0"
    MCAST_ADDR = "237.252.249.227"
    MCAST_PORT = 32000

    node_id = None
    service = None

    def __init__(self, port_random=False, ioloop=None, node_id=None):

        super(ZeroMQMedium, self).__init__(node_id)

        if ioloop is None:
            ioloop = IOLoop.instance()
        self.ioloop = ioloop

        # ØMQ Sockets
        self.context = zmq.Context.instance()

        self.sub = ZMQStream(stream(self.context, zmq.SUB,
            bind=False), self.ioloop)
        self.sub.on_recv(self.process_sub)

        if port_random:
            self.server, self.server_port = stream(self.context,
                zmq.ROUTER, addr='tcp://*', bind=True, random=True)
            self.server = ZMQStream(self.server, self.ioloop)
            self.server.on_recv(self.process_raw_query)
            # Set node id
            self.server.socket.setsockopt(zmq.IDENTITY,
                                          self.node_id.encode('utf-8'))

            self.pub, self.pub_port = stream(self.context, zmq.PUB,
                addr='tcp://*', bind=True, random=True)
            self.pub = ZMQStream(self.pub, self.ioloop)

        # UDP Socket
        self.udp_socket = self.create_udp_socket()
        self.udp_fileno = self.udp_socket.fileno()
        self.ioloop.add_handler(self.udp_socket.fileno(),
                                self.process_register, IOLoop.READ)

    def start(self):
        self.logger.debug('Start ioloop')
        self.ioloop.start()

    def stop(self):
        self.logger.debug('Stop ioloop')
        self.ioloop.stop()

    def get_node_info(self):
        node_info = super(ZeroMQMedium, self).get_node_info()

        node_info['server_port'] = self.server_port
        node_info['pub_port'] = self.pub_port

        return node_info

    def add_server_entrypoint(self, path=None, port=None, publish=False,
            callback=None):
        if path is not None:
            # Ensure path exists
            try:
                makedirs(path)
            except OSError:
                # Path exists
                pass

            socket_path = 'ipc://%s' % join(path, 'server.sock')
            socket = stream(self.context, zmq.ROUTER, addr=socket_path,
                bind=True)
            zmqstream = ZMQStream(socket, self.ioloop)

            if callback:
                zmqstream.on_recv(callback)
            else:
                zmqstream.on_recv(self.process_raw_query)

            return socket_path, socket

    def add_republisher(self, path):
        socket_path = 'ipc://%s' % join(path, 'server-publish.sock')
        socket = stream(self.context, zmq.PUB, addr=socket_path,
            bind=True)
        self.events_republishers.append(socket)
        return socket_path, socket

    def create_udp_socket(self):
        sock = socket.socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            sock.setsockopt(SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, 255)
        sock.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP,
            inet_aton(self.MCAST_ADDR) + inet_aton(self.ANY))

        sock.bind((self.ANY, self.MCAST_PORT))
        return sock

    def register(self):
        self.logger.info('Register')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
            socket.IPPROTO_UDP)
        sock.bind((self.ANY, 0))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.sendto(json.dumps(self.get_node_info()).encode('utf-8'),
                (self.MCAST_ADDR, self.MCAST_PORT))

    def subscribe(self, topic):
        self.sub.setsockopt(zmq.SUBSCRIBE, topic.encode('utf-8'))

    def process_sub(self, event_message):
        self.logger.info('Process raw sub: %s' % event_message)
        message_type, data = event_message[0].decode('utf-8').split(' ', 1)
        data = json.loads(data)

        self.logger.info('Process sub, message_type: %s, data: %s' %
            (message_type, data))

        self.process_event(message_type, data)

        # for socket in self.events_republishers:
        #     self.logger.info('Republish %s on %s' % (message[0], socket))
        #     import time; time.sleep(1)
        #     socket.send(message[0])

    def process_raw_query(self, raw_message):
        self.logger.info('Raw message %s', raw_message)
        sender_uuid, message_type, message = raw_message
        message = json.loads(message.decode('utf-8'))
        message_type = message_type.decode('utf-8')

        self.logger.info('Process raw query, message_type: %s, message: %s' %
            (message_type, message))

        result = self.process_message(message, message_type)

        if result:
            self.server.send_multipart((sender_uuid, json.dumps(result).encode('utf-8')))


    def process_register(self, *args):
        data, address = self.udp_socket.recvfrom(1024)
        self.logger.info('Process register, data: %s, from %s' %
            (data, address[0]))
        registraton_message = json.loads(data.decode('utf-8'))
        address = (address[0], self.MCAST_PORT)
        registraton_message['address'] = address[0]

        self.process_message(registraton_message, 'register')
        # if self.save_register_info(data):
        #     self.register_to(data)
        # self.logger.info('Self ressources map: %s' % self.services_ressources)

    def send_registration_answer(self, peer_info):
        node_info = self.get_node_info()

        # Find my local address
        s = socket.socket(AF_INET, SOCK_STREAM)
        s.connect((peer_info['address'], peer_info['server_port']))
        node_info['address'] = s.getsockname()[0]

        super(ZeroMQMedium, self).send_registration_answer(peer_info, node_info)

    def connect_to_node(self, peer_info):
        peer_address = 'tcp://%s:%s' % (peer_info['address'],
                                        peer_info['pub_port'])
        self.logger.debug('Connecting my sub socket to %s' % peer_address)
        self.sub.connect(peer_address)
        # Wait for subscribing process to be completed
        time.sleep(0.01)

    def publish(self, event_type, event_data):
        self.logger.debug("Publish %s %s" % (event_type, event_data))
        pub_message = '%s %s' % (event_type, json.dumps(event_data))
        pub_message = pub_message.encode('utf-8')
        self.pub.send(pub_message)

    def send(self, peer_info, message, message_type="message", callback=None,
             wait_response=True):
        address = peer_info['address']
        port = peer_info['server_port']
        request_socket = self.context.socket(zmq.DEALER)
        address = 'tcp://%(address)s:%(port)s' % locals()
        request_socket.connect(address)

        if callback and wait_response:
            def on_recv(message):
                callback(json.loads(message[0].decode('utf-8')))

            stream = ZMQStream(request_socket, self.ioloop)
            stream.on_recv(on_recv)

        log_info = (message_type, json.dumps(message), address)
        self.logger.info('Send %s/%s to %s' % log_info)
        message = (message_type.encode('utf-8'), json.dumps(message).encode('utf-8'))
        request_socket.send_multipart(message)

        if not wait_response:
            request_socket.close()
            return

        if not callback:
            return self._sync_get_response(request_socket)

    def _sync_get_response(self, socket):
        return json.loads(socket.recv_multipart()[0].decode('utf-8'))

    def close(self):
        self.logger.info('Close medium')
        try:
            self.publish('close', self.get_node_info())
            self.pub.flush()
        except OSError as e:
            # Log error
            self.logger.error('Error during leaving announcement')

        # Stop receiving data
        self.ioloop.remove_handler(self.udp_fileno)
        self.udp_socket.close()
        self.sub.close()
        self.server.close()
        self.pub.close()
