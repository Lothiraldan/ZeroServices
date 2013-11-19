import zmq
import time
import json
import socket
import logging

from mock import Mock, create_autospec

from zeroservices.exceptions import ServiceUnavailable
from zeroservices.service import RessourceCollection


class TestMedium(object):

    def __init__(self):
        self.node_id = None
        self.send_registration_answer = Mock()
        self.send = Mock()
        self.connect_to_node = Mock()


class ServiceRegistry(object):
    SERVICES = {}
    SERVICES_RESSOURCES = {}


def sample_collection(sample_ressource_name):

    collection = create_autospec(RessourceCollection, True)
    collection.ressource_name = sample_ressource_name

    return collection


def gen_service(base_service, save_entries=None):

    if save_entries is None:
        save_entries = False

    class TestService(base_service):

        def __init__(self):
            self.queries = []
            self.events = []
            self.save_entries = save_entries
            self.logger = logging.getLogger()

        def main(self):
            pass

        def stop(self):
            del ServiceRegistry.SERVICES[self.name]
            for ressource in self.ressources:
                del ServiceRegistry.SERVICES_RESSOURCES[ressource]

        def register(self):
            ServiceRegistry.SERVICES[self.name] = self
            for ressource in self.ressources:
                ServiceRegistry.SERVICES_RESSOURCES[ressource] = self

        def call(self, action, **kwargs):
            service, action = map(str, action.split('.', 1))
            kwargs = {str(key): value for key, value in kwargs.items()}
            return ServiceRegistry.SERVICES[service].process_query((action, json.dumps(kwargs)))

        def publish(self, etype, event):
            raw_event = ('%s %s' % (etype, event),)
            for service in ServiceRegistry.SERVICES.values():
                if service != self:
                    service.process_event(raw_event)

        def process_query(self, query):
            if self.save_entries:
                self.queries.append(query)
            return super(TestService, self).process_query(query)

        def process_event(self, event):
            if self.save_entries:
                self.events.append(event)
            super(TestService, self).process_event(event)

    return TestService()

# Test memory medium

SERVICES = {}
RESSOURCES = {}

class MemoryMedium(object):

    def __init__(self, service_info, event_callback, msg_callback,
            port_random=False):
        self.service_info = service_info
        self.service_name = service_info['name']

        # Callbacks
        self.event_callback = event_callback
        self.msg_callback = msg_callback

        SERVICES[service_info['name']] = self

        for ressource in service_info.get('ressources', []):
            RESSOURCES[ressource] = self

        self.logger = logging.getLogger(self.service_info['name'])

    def register(self):
        pass

    def start(self):
        pass

    def process_sub(self, message_type, data):
        self.logger.info('Process sub, message_type: %s, data: %s' %
            (message_type, data))
        self.event_callback(message_type, data)

    def process_raw_query(self, message_type, message):
        self.logger.info('Process raw query, message_type: %s, message: %s' %
            (message_type, message))

        return self.msg_callback(message_type, **message)

    def publish(self, event_type, event_data):
        for service in [s for s in SERVICES.values() if s.service_name != self.service_name]:
            service.process_sub(event_type, event_data)

    def call(self, action, **kwargs):
        service_id, action = map(str, action.split('.', 1))

        try:
            service = RESSOURCES[service_id]
        except KeyError:
            raise ServiceUnavailable('Service %s is unavailable.' % service_id)

        return service.process_raw_query(action, kwargs)

    def close(self):
        del SERVICES[self.service_info['name']]
        for ressource in self.service_info.get('ressources', []):
            del RESSOURCES[ressource]
