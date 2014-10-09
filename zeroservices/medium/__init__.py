import logging

from uuid import uuid4
from abc import ABCMeta, abstractmethod


class BaseMedium(object):

    __metaclass__ = ABCMeta
    node_id = None

    def __init__(self, node_id):
        # Node id
        if node_id is None:
            node_id = uuid4().hex
        self.node_id = node_id

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def register(self):
        pass

    @abstractmethod
    def subscribe(self, topic):
        pass

    def get_node_info(self):
        node_info = self.service.service_info()
        node_info['node_id'] = self.node_id

        return node_info

    @abstractmethod
    def publish(self, event_type, event_data):
        pass

    def process_event(self, message_type, event_message):
        if message_type == 'close':
            self.service.on_peer_leave(event_message)
        elif message_type == 'register':
            self.service.on_registration_message(event_message)
        else:
            self.service.on_event(message_type, event_message)

    @abstractmethod
    def send(self, peer_info, message, messsage_type="message", callback=None,
             wait_response=True):
        pass

    def process_message(self, message, message_type):
        if message_type == 'register':
            self.service.on_registration_message(message)
        else:
            return self.service.on_message(message_type=message_type,
                                           **message)

    @abstractmethod
    def connect_to_node(self, peer_info):
        pass

    @abstractmethod
    def periodic_call(self, callback_time, callback):
        pass

    def send_registration_answer(self, peer_info, node_info=None):
        if node_info is None:
            node_info = self.get_node_info()

        self.send(peer_info, node_info, 'register', wait_response=False)

    def set_service(self, service):
        self.service = service

        self.logger = logging.getLogger('%s.%s' % (service.name,
            'medium'))
        self.logger.setLevel(logging.DEBUG)

        self.logger.info('Set service %s, node_info: %s' %
            (service.name, self.get_node_info()))


from .zeromq import ZeroMQMedium
