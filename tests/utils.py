try:
    from unittest.mock import Mock, create_autospec
except ImportError:
    from mock import Mock, create_autospec

from unittest import TestCase as unittestTestCase

from zeroservices.exceptions import ServiceUnavailable
from zeroservices.ressources import (RessourceCollection, Ressource,
                                     is_callable, RessourceService)
from zeroservices.medium import BaseMedium
from zeroservices import BaseService
from zeroservices.query import match


class TestCase(unittestTestCase):

    def assertItemsEqual(self, *args):
        if hasattr(self, 'assertCountEqual'):
            return self.assertCountEqual(*args)
        return super(TestCase, self).assertItemsEqual(*args)


def test_medium():
    return Mock(spec_set=BaseMedium)


class ServiceRegistry(object):
    SERVICES = {}
    SERVICES_RESSOURCES = {}


def sample_collection(sample_ressource_name):

    collection = create_autospec(RessourceCollection, True)
    collection.ressource_name = sample_ressource_name

    return collection


def sample_ressource():
    ressource_class = create_autospec(Ressource, True)
    ressource_instance = create_autospec(Ressource, True, instance=True)
    ressource_class.return_value = ressource_instance
    return ressource_class, ressource_instance


def sample_service():
    service = create_autospec(RessourceService, True, instance=True)
    return service


def base_ressource():

    class BaseRessource(Ressource):

        def add_link(self):
            pass

        def create(self):
            pass

        def delete(self):
            pass

        def get(self):
            pass

        def patch(self):
            pass

    return BaseRessource


class TestService(BaseService):

    def __init__(self, *args, **kwargs):
        super(TestService, self).__init__(*args, **kwargs)
        self.on_message = create_autospec(self.on_message, return_value=None)
        self.on_event = create_autospec(self.on_event, return_value=None)

# Test memory medium

SERVICES = {}
SERVICES_LIST = []


class MemoryMedium(BaseMedium):

    def __init__(self, node_id):
        super(MemoryMedium, self).__init__(node_id)
        self.topics = []
        self.callbacks = []

    def register(self):
        self.logger.info('Register %s', self.get_node_info())

        # Register myself to global
        SERVICES[self.node_id] = self
        SERVICES_LIST.append(self)

        self.publish('register', self.get_node_info())

    def start(self):
        pass

    def close(self):
        del SERVICES[self.node_id]
        SERVICES_LIST.remove(self)

    def connect_to_node(self, peer_info):
        pass

    def subscribe(self, topic):
        self.topics.append(topic)

    def process_sub(self, message_type, data):
        self.logger.info('Process sub, message_type: %s, data: %s' %
            (message_type, data))
        self.event_callback(message_type, data)

    def process_raw_query(self, message_type, message):
        self.logger.info('Process raw query, message_type: %s, message: %s' %
            (message_type, message))

        return self.msg_callback(message_type, **message)

    def publish(self, event_type, event_data):
        for service in [s for s in SERVICES_LIST if s.node_id != self.node_id]:
            service.process_event(event_type, event_data)

    def send(self, peer_info, message, message_type="message", callback=None,
             wait_response=True):
        try:
            service = SERVICES[peer_info['node_id']]
        except KeyError:
            raise ServiceUnavailable('Service %s is unavailable.' % peer_info['node_id'])

        return service.process_message(message, message_type)

    def periodic_call(self, callback, callback_time):
        self.callbacks.append(callback)

    def call_callbacks(self):
        for callback in self.callbacks:
            callback()

# Memory Collection


class MemoryRessource(Ressource):

    def __init__(self, collection, **kwargs):
        super(MemoryRessource, self).__init__(**kwargs)
        self.collection = collection

    @is_callable
    def create(self, ressource_data):
        self.collection[self.ressource_id] = ressource_data
        self.publish('create', {'action': 'create', 'ressource_data': ressource_data})
        return {'ressource_id': self.ressource_id}

    @is_callable
    def get(self):
        try:
            ressource = {'ressource_id': self.ressource_id,
                         'ressource_data': self.collection[self.ressource_id]}
        except KeyError:
            return 'NOK'
        return ressource

    @is_callable
    def patch(self, patch):
        ressource = self.collection[self.ressource_id]

        set_keys = patch['$set']
        for key, value in set_keys.items():
            ressource[key] = value

        self.publish('patch', {'action': 'patch', 'patch': patch})

        return ressource

    @is_callable
    def delete(self):
        del self.collection[self.ressource_id]
        self.publish('delete', {'action': 'delete'})
        return 'OK'

    @is_callable
    def add_link(self, relation, target_id, title):
        target_relation = target_id[0]
        ressource = self.collection[self.ressource_id]
        links = ressource.setdefault('_links', {})
        links.setdefault(relation, []).append({'target_id': target_id,
                                                 'title': title})
        links.setdefault('latest', {})[target_relation] = target_id
        self.publish('add_link', {'action': 'add_link', 'target_id': target_id,
                      'title': title, 'relation': relation})
        return 'OK'


class MemoryCollection(RessourceCollection):

    def __init__(self, collection_name):
        super(MemoryCollection, self).__init__(MemoryRessource, collection_name)
        self._collection = {}

    def instantiate(self, **kwargs):
        return super(MemoryCollection, self).instantiate(
            collection=self._collection, **kwargs)

    @is_callable
    def list(self, where=None):
        ressources = []
        for ressource_id, ressource_data in self._collection.items():

            # Filtering happens here
            if where:
                if not match(where, ressource_data):
                    continue

            ressources.append({'ressource_id': ressource_id,
                               'ressource_data': ressource_data})

        return ressources
