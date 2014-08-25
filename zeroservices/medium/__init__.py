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

    @abstractmethod
    def get_node_info(self):
        pass

    @abstractmethod
    def publish(self, event_type, event_data):
        pass

    @abstractmethod
    def send(self, peer_info, message, msg_type="message", callback=None,
             wait_response=True):
        pass

    @abstractmethod
    def connect_to_node(self, peer_info):
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

        self.logger.info('Start %s, listen to %s and publish to %s' %
            (service.name, self.server_port, self.pub_port))


from .zeromq import ZeroMQMedium
