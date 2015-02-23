import logging

from uuid import uuid4
from abc import ABCMeta, abstractmethod
from ..utils import maybe_asynchronous

import asyncio


class BaseMedium(object):

    __metaclass__ = ABCMeta
    node_id = None

    def __init__(self, loop, discovery_class, node_id=None):
        # Node id
        if node_id is None:
            node_id = uuid4().hex
        self.node_id = node_id
        self.directory = {}

        self.loop = loop
        self.discovery = None
        self.discovery_class = discovery_class
        self.event_listeners = set()
        self.server_sockets = set()

    @asyncio.coroutine
    def start(self):
        self.discovery = self.discovery_class(self.process_message, self.loop,
                                              self.get_node_info())

        yield from self.discovery.start()
        yield from self.discovery.send_registration_infos()

    def close(self):
        # If start has not been called, do not try to close discovery
        if self.discovery:
            self.discovery.close()

    @abstractmethod
    def register(self):
        pass

    @abstractmethod
    def subscribe(self, topic):
        pass

    def get_node_info(self):
        service_info = self.service.service_info()
        service_info['node_id'] = self.node_id
        return {'node_id': self.node_id, 'service_info': service_info}

    @abstractmethod
    def publish(self, event_type, event_data):
        pass

    def process_event(self, message_type, event_message):
        for event_listener in self.event_listeners:
            yield from event_listener(message_type, event_message)

    @abstractmethod
    def send(self, node_id, message, message_type="message", wait_response=True):
        pass

    @asyncio.coroutine
    def process_message(self, message_type, message, sender=None):
        self.logger.info("Process [{}] {}".format(message_type, message))
        if message_type == 'register':
            service_info = message.pop('service_info')
            yield from self.process_registration(message)
            return self.service.on_registration_message(service_info)
        else:
            result = yield from self.on_message_callback(message_type=message_type, **message)
            if sender:
                yield from self.respond(sender, result)
                return ('message', result)

            return result

    @abstractmethod
    def connect_to_node(self, node_if):
        pass

    def periodic_call(self, callback, delay):

        def periodic_wrapper():
            self.loop.create_task(callback())
            self.loop.call_later(delay, periodic_wrapper)

        return self.loop.call_later(delay, periodic_wrapper)

    def send_registration_answer(self, node_id, node_info=None):
        if node_info is None:
            node_info = self.get_node_info()

        result = yield from self.send(node_id, node_info, 'register', wait_response=False)
        return result

    def set_service(self, service):
        self.service = service

        self.logger = logging.getLogger('%s.%s' % (service.name,
            'medium'))
        self.logger.setLevel(logging.DEBUG)

        self.on_message_callback = service.on_message
        self.event_listeners.add(service.process_event)

        # self.logger.info('Set service %s, node_info: %s' %
        #     (service.name, self.get_node_info()))

    def process_registration(self, message):
        node_id = message['node_id']

        if node_id not in self.directory:
            self.directory[node_id] = message

            yield from self.send_registration_answer(node_id)

    def get_directory(self):
        return self.directory

    def add_event_listener(self, event_listener):
        self.event_listeners.add(event_listener)

    def check_leak(self):
        if self.discovery:
            return self.discovery.check_leak()


from .zeromq import ZeroMQMedium
