import logging

from zeroservices.medium.zeromq import ZeroMQMedium
from zeroservices.exceptions import UnknownNode
from zeroservices.validation import REGISTRATION_SCHEMA, MultipleInvalid

logging.basicConfig(level=logging.DEBUG)

DEFAULT_MEDIUM = ZeroMQMedium


class BaseService(object):

    medium = None
    nodes_directory = {}
    name = None

    def __init__(self, name, medium):
        self.name = name
        self.medium = medium
        self.medium.set_service(self)
        self.nodes_directory = {}
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
        if node_info['node_id'] in self.nodes_directory:
            return

        self.save_new_node_info(node_info)
        self.medium.connect_to_node(node_info)
        self.medium.send_registration_answer(node_info)
        self.on_peer_join(node_info)

    def on_registration_message_worker(self, node_info):
        pass

    def save_new_node_info(self, node_info):
        self.nodes_directory[node_info['node_id']] = node_info

    def get_known_nodes(self):
        return self.nodes_directory.keys()

    def on_peer_join(self, node_info):
        pass

    def on_peer_leave(self, node_info):
        pass

    def on_message(self, message_type, *args, **kwargs):
        pass

    def on_event(self, message_type, *args, **kwargs):
        pass

    def send(self, node_id, message, **kwargs):
        try:
            node_info = self.nodes_directory[node_id]
        except KeyError:
            raise UnknownNode("Unknown node {0}".format(node_id))
        return self.medium.send(node_info, message, **kwargs)

    def publish(self, *args):
        self.medium.publish(*args)

    def main(self):
        self.medium.register()
        self.medium.start()

    def close(self):
        self.medium.close()
