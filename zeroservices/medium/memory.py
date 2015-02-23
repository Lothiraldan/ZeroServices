import asyncio
import json

from ..medium import BaseMedium
from ..resources import (ResourceCollection, Resource,
                         is_callable)
from ..exceptions import ServiceUnavailable
from ..query import match


# Test memory medium
class MemoryMedium(BaseMedium):

    NODES = {}

    def __init__(self, loop, discovery_class, node_id=None):
        super().__init__(loop, discovery_class, node_id)

        self.topics = []
        self.callbacks = []

    @classmethod
    def reset(cls):
        cls.NODES = {}

    def close(self):
        try:
            del self.NODES[self.node_id]
        except KeyError:
            pass
        super().close()

    @asyncio.coroutine
    def start(self):
        self.NODES[self.node_id] = self
        yield from super().start()

    def connect_to_node(self, node_id):
        pass

    def subscribe(self, topic):
        self.topics.append(topic)

    @asyncio.coroutine
    def publish(self, event_type, event_data):
        for node in self.NODES.values():
            if node.node_id == self.node_id:
                continue
            yield from node.process_event(event_type, event_data)

    @asyncio.coroutine
    def send(self, node_id, message, message_type="message", wait_response=True):
        try:
            node = self.NODES[node_id]
        except KeyError:
            raise ServiceUnavailable('Service %s is unavailable.' % node_id)

        # Be sure that message could be dumped in json
        message = json.dumps(message)

        result = yield from node.process_message(message_type, json.loads(message),
                                                 sender=self.node_id)

        if wait_response:
            assert result[0] == 'message'
            return result[1]

        return

    @asyncio.coroutine
    def respond(self, sender, message, message_type="message"):
        return

    def send_registration_answer(self, node_id, node_info=None):
        node_info = self.get_node_info()

        node_info['address'] = "127.0.0.1"

        return super(MemoryMedium, self).send_registration_answer(node_id, node_info)

    def periodic_call(self, callback, delay):
        super().periodic_call(callback, delay)
        self.callbacks.append(callback)

    @asyncio.coroutine
    def call_callbacks(self):
        for callback in self.callbacks:
            yield from callback()

    def check_leak(self):
        super().check_leak()
        if self.NODES:
            nodes = self.NODES
            self.NODES = {}
            raise Exception(nodes)
