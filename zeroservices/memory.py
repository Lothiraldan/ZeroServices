from .medium import BaseMedium
from .resources import (ResourceCollection, Resource,
                         is_callable)
from .exceptions import ServiceUnavailable
from .query import match


# Test memory medium

SERVICES = {}
SERVICES_LIST = []


class MemoryMedium(BaseMedium):

    def __init__(self, node_id):
        super(MemoryMedium, self).__init__(node_id)
        self.topics = []
        self.callbacks = []

        # Testing utils
        self.published_messages = []

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
        self.published_messages.append((event_type, event_data))
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


class MemoryResource(Resource):

    def __init__(self, collection, **kwargs):
        super(MemoryResource, self).__init__(**kwargs)
        self.collection = collection

    @is_callable
    def create(self, resource_data):
        resource_data = super(MemoryResource, self).create(resource_data)
        self.collection[self.resource_id] = resource_data
        self.publish('create', {'action': 'create', 'resource_data': resource_data})
        return {'resource_id': self.resource_id}

    @is_callable
    def get(self):
        try:
            resource = {'resource_id': self.resource_id,
                         'resource_data': self.collection[self.resource_id]}
        except KeyError:
            return 'NOK'
        return resource

    @is_callable
    def patch(self, patch):
        patch = super(MemoryResource, self).patch(patch)
        resource = self.collection[self.resource_id]

        set_keys = patch['$set']
        for key, value in set_keys.items():
            resource[key] = value

        self.publish('patch', {'action': 'patch', 'patch': patch})

        return resource

    @is_callable
    def delete(self):
        del self.collection[self.resource_id]
        self.publish('delete', {'action': 'delete'})
        return 'OK'

    @is_callable
    def add_link(self, relation, target_id, title):
        target_relation = target_id[0]
        resource = self.collection[self.resource_id]
        links = resource.setdefault('_links', {})
        links.setdefault(relation, []).append({'target_id': target_id,
                                                 'title': title})
        links.setdefault('latest', {})[target_relation] = target_id
        self.publish('add_link', {'action': 'add_link', 'target_id': target_id,
                      'title': title, 'relation': relation})
        return 'OK'


class MemoryCollection(ResourceCollection):

    def __init__(self, collection_name, resource_class=None):
        if resource_class is None:
            resource_class = MemoryResource
        super(MemoryCollection, self).__init__(resource_class, collection_name)
        self._collection = {}

    def instantiate(self, **kwargs):
        return super(MemoryCollection, self).instantiate(
            collection=self._collection, **kwargs)

    @is_callable
    def list(self, where=None):
        resources = []
        for resource_id, resource_data in self._collection.items():

            # Filtering happens here
            if where:
                if not match(where, resource_data):
                    continue

            resources.append({'resource_id': resource_id,
                               'resource_data': resource_data})

        return resources
