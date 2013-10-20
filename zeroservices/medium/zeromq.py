# -*- coding: utf-8 -*-
import sys
import zmq
import time
from zmq.eventloop import ioloop
ioloop.install()
from zmq.eventloop.zmqstream import ZMQStream
import json
import logging
import socket

from zeroservices.exceptions import ServiceUnavailable

from socket import gethostname, getaddrinfo, AF_INET, SOCK_STREAM, SOCK_DGRAM, IPPROTO_UDP, SOL_SOCKET, SO_REUSEADDR, IPPROTO_IP, IP_MULTICAST_TTL, IP_ADD_MEMBERSHIP, inet_aton
from tornado import gen
from os.path import join
from os import makedirs

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
            sock.setsockopt(zmq.SUBSCRIBE, '')

    if random:
        return sock, int(port)
    else:
        return sock


class ZeroMQMedium(object):

    #Multicast registration
    ANY = "0.0.0.0"
    MCAST_ADDR = "237.252.249.227"
    MCAST_PORT = 32000

    def __init__(self, service, port_random=False):
        self.service = service
        self.service_info = service.service_info()
        self.ioloop = ioloop.IOLoop.instance()

        self.logger = logging.getLogger('%s.%s' % (self.service_info['name'],
            'medium'))
        self.logger.setLevel(logging.DEBUG)

        # ØMQ Sockets
        self.context = zmq.Context.instance()
        ioloop.install()

        self.sub = ZMQStream(stream(self.context, zmq.SUB,
            bind=False))
        self.sub.on_recv(self.process_sub)

        if port_random:
            self.server, self.server_port = stream(self.context,
                zmq.ROUTER, addr='tcp://*', bind=True, random=True)
            self.server = ZMQStream(self.server)
            self.server.on_recv(self.process_raw_query)

            self.pub, self.pub_port = stream(self.context, zmq.PUB,
                addr='tcp://*', bind=True, random=True)
            self.pub = ZMQStream(self.pub)

        # UDP Socket
        self.udp_socket = self.create_udp_socket()
        ioloop.IOLoop.instance().add_handler(self.udp_socket.fileno(),
            self.process_register, ioloop.IOLoop.READ)

        self.service_info['server_port'] = self.server_port
        self.service_info['pub_port'] = self.pub_port

        self.logger.info('Start %s, listen to %s and publish to %s' %
            (self.service_info['name'], self.server_port, self.pub_port))

        self.address = getaddrinfo(gethostname(), None, AF_INET, SOCK_STREAM)[0][4][0]

        # import sys
        # self.ioloop.instance().handle_callback_exception(lambda *args: raise Exception(args))

    def start(self):
        self.ioloop.start()

    def stop(self):
        self.ioloop.stop()

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
            zmqstream = ZMQStream(socket)

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

        sock.sendto(json.dumps(self.service_info),
                (self.MCAST_ADDR, self.MCAST_PORT))

    def process_sub(self, message):
        self.logger.info('Process raw sub: %s' % message)
        message_type, data = message[0].split(' ', 1)
        data = json.loads(data)

        self.logger.info('Process sub, message_type: %s, data: %s' %
            (message_type, data))
        self.service.on_event(message_type, data)

        # for socket in self.events_republishers:
        #     self.logger.info('Republish %s on %s' % (message[0], socket))
        #     import time; time.sleep(1)
        #     socket.send(message[0])

    @gen.coroutine
    def process_raw_query(self, raw_message):
        self.logger.info('Raw message %s', raw_message)
        sender_uuid, message_type, message = raw_message
        message = json.loads(message)

        self.logger.info('Process raw query, message_type: %s, message: %s' %
            (message_type, message))

        if message_type == 'register':
            self.service.on_registration_message(message)
        else:
            self.service.on_message(message_type, message)
            # result = yield gen.Task(self.msg_callback, **message)
            # self.server.send_multipart((sender_uuid, json.dumps(result)))

    def process_register(self, *args):
        data, address = self.udp_socket.recvfrom(1024)
        self.logger.info('Process register, data: %s, from %s' %
            (data, address[0]))
        data = json.loads(data)
        address = (address[0], self.MCAST_PORT)
        data['address'] = address[0]
        self.service.on_registration_message(data)
        # if self.save_register_info(data):
        #     self.register_to(data)
        # self.logger.info('Self ressources map: %s' % self.services_ressources)

    def save_register_info(self, data):
        service_name = data.pop('name')
        if service_name in self.services:
            return False

        if service_name == self.service_info['name']:
            return False

        self.logger.debug('Connecting my sub socket to tcp://%s:%s' %
            (data['address'], data['pub_port']))
        self.sub.connect('tcp://%s:%s' % (data['address'], data['pub_port']))

        # Find my ip to reach peer
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((data['address'], data['server_port']))
        data['me'] = s.getsockname()[0]

        # Service ressources
        ressources = data.pop('ressources', [])
        for ressource in ressources:
            self.services_ressources[ressource] = data

        self.services[service_name] = data

        return True

    def send_registration_answer(self, data):
        sock = self.context.socket(zmq.DEALER)
        sock.connect('tcp://%s:%s' % (data['address'], data['server_port']))
        info = self.service_info

        # Find my local address
        s = socket.socket(AF_INET, SOCK_STREAM)
        s.connect((data['address'], data['server_port']))
        info['address'] = s.getsockname()[0]

        self.logger.info('Sending my registration info to %s' % data['address'])
        sock.send_multipart(('register', json.dumps(self.service_info)))
        sock.close()

    def connect_to_node(self, data):
        self.logger.debug('Connecting my sub socket to tcp://%s:%s' %
            (data['address'], data['pub_port']))
        self.sub.connect('tcp://%s:%s' % (data['address'], data['pub_port']))
        # Wait for subscribing process to be completed
        time.sleep(0.01)

    def register_to(self, data):
        sock = self.context.socket(zmq.DEALER)
        sock.connect('tcp://%s:%s' % (data['address'], data['server_port']))
        info = self.service_info
        info['address'] = data['me']
        self.logger.info('Sending my registration info to %s' % data['address'])
        sock.send_multipart(('register', json.dumps(self.service_info)))
        sock.close()

    def publish(self, event_type, event_data):
        self.logger.debug("Publish %s %s" % (event_type, event_data))
        self.pub.send('%s %s' % (event_type, json.dumps(event_data)))

    def send(self, address, port, message, msg_type="message"):
        request_socket = self.context.socket(zmq.DEALER)
        address = 'tcp://%(address)s:%(port)s' % locals()
        request_socket.connect(address)

        request_socket.send_multipart((msg_type, json.dumps(message)))


    def call(self, collection, msg_type="service", callback=None, **kwargs):
        try:
            service_address = self.services_ressources[collection]
        except KeyError:
            raise ServiceUnavailable('Service %s is unavailable. %s' % (collection, self.services_ressources))

        # Create socket
        request_socket = self.context.socket(zmq.DEALER)
        address = 'tcp://%(address)s:%(server_port)s' % service_address
        request_socket.connect(address)

        stream = ZMQStream(request_socket)
        if callback:
            stream.on_recv(callback)

        # Make call
        kwargs = {str(key): value for key, value in kwargs.items()}
        kwargs['collection'] = collection
        self.logger.info("Call %s with %s" % (collection, kwargs))
        request_socket.send_multipart((msg_type, json.dumps(kwargs)))

        if not callback:
            return json.loads(request_socket.recv_multipart()[0])

    def close(self):
        self.logger.info('Close medium')
        self.pub.close()
        self.sub.close()
        self.server.close()
        self.ioloop.remove_handler(self.udp_socket.fileno())