import asyncio
import logging

from asyncio import coroutine
from copy import copy

from zeroservices.medium.zeromq import ZeroMQMedium
from zeroservices.exceptions import UnknownNode
from zeroservices.validation import REGISTRATION_SCHEMA, MultipleInvalid

logging.basicConfig(level=logging.DEBUG)

DEFAULT_MEDIUM = ZeroMQMedium


class BaseService(object):

    medium = None
    name = None

    def __init__(self, name, medium):
        self.name = name
        self.medium = medium
        self.medium.set_service(self)
        self.directory = {}
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

    def service_info(self):
        """Subclass to return informations for registration
        """
        return {'name': self.name, 'node_type': 'node'}

    def on_registration_message(self, node_info):
        try:
            REGISTRATION_SCHEMA(node_info)
        except MultipleInvalid as e:
            message = "Invalid node_info: {}, raise Exception {}".format(node_info, e)
            logging.exception(message)
            return

        if node_info['node_id'] == self.medium.node_id:
            return

        if node_info['node_type'] == 'node':
            self.on_registration_message_node(node_info)
        elif node_info['node_type'] == 'worker':
            self.on_registration_message_worker(node_info)

    def on_registration_message_node(self, node_info):
        if node_info['node_id'] in self.directory:
            return

        self.save_new_node_info(node_info)
        self.medium.connect_to_node(node_info['node_id'])
        self.medium.send_registration_answer(node_info['node_id'])
        self.on_peer_join(node_info)

    def on_registration_message_worker(self, node_info):
        pass

    def save_new_node_info(self, node_info):
        self.directory[node_info['node_id']] = copy(node_info)

    def get_known_nodes(self):
        return self.directory.keys()

    def on_peer_join(self, node_info):
        pass

    def on_peer_leave(self, node_info):
        pass

    @asyncio.coroutine
    def on_message(self, message_type, *args, **kwargs):
        pass

    @asyncio.coroutine
    def process_event(self, message_type, event_message):
        if message_type == 'close':
            return self.service.on_peer_leave(event_message)
        elif message_type == 'register':
            return self.service.on_registration_message(event_message)
        else:
            result = yield from self.on_event(message_type, **event_message)
            return result

    @asyncio.coroutine
    def on_event(self, message_type, *args, **kwargs):
        pass

    def send(self, node_id, message, **kwargs):
        return self.medium.send(node_id, message, **kwargs)

    def publish(self, *args, **kwargs):
        return self.medium.publish(*args, **kwargs)

    @coroutine
    def start(self):
        yield from self.medium.start()

    def get_directory(self):
        return self.directory

    def close(self):
        return self.medium.close()
