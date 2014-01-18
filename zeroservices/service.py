import sys
import json
import logging
import traceback

from copy import copy
from tornado import gen

from zeroservices.medium.zeromq import ZeroMQMedium
from zeroservices.utils import maybe_asynchronous

logging.basicConfig(level=logging.DEBUG)

DEFAULT_MEDIUM = ZeroMQMedium


class BaseService(object):

    medium = None
    nodes_directory = {}
    name = None

    def __init__(self, name, medium):
        self.name = name
        self.medium = medium
        self.medium.service = self
        self.nodes_directory = {}

    def service_info(self):
        """Subclass to return informations for registration
        """
        return {'name': self.name}

    def on_registration_message(self, node_info):
        if node_info['node_id'] == self.medium.node_id:
            return

        if node_info['node_id'] in self.nodes_directory:
            return

        self.save_new_node_info(node_info)
        self.medium.connect_to_node(node_info)
        self.medium.send_registration_answer(node_info)
        self.on_peer_join(node_info)

    def save_new_node_info(self, node_info):
        self.nodes_directory[node_info['node_id']] = node_info

    def on_peer_join(self, node_info):
        pass

    def on_peer_leave(self, node_info):
        pass

    def on_message(self, *args, **kwargs):
        pass

    def on_event(self, *args, **kwargs):
        pass

    def send(self, node_id, message, **kwargs):
        return self.medium.send(self.nodes_directory[node_id], message, **kwargs)

    def publish(self, *args):
        self.medium.publish(*args)

    def main(self):
        self.medium.register()
        self.medium.start()

    def close(self):
        self.medium.close()
