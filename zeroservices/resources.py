import asyncio

from .service import BaseService
from .exceptions import UnknownService, ResourceException
from .query import match
from .utils import accumulate
from abc import ABCMeta, abstractmethod
from uuid import uuid4

import logging


### Utils


def is_callable(method):
    method.is_callable = True
    return asyncio.coroutine(method)


class BaseResourceService(BaseService):

    application = None

    def __init__(self, name, medium):
        self.resources = {}
        self.resources_directory = {}
        self.resources_worker_directory = {}
        super().__init__(name, medium)

    def save_new_node_info(self, node_info):
        super().save_new_node_info(node_info)

        for resource in node_info.get('resources', ()):
            self.resources_directory[resource] = node_info['node_id']

    @asyncio.coroutine
    def send(self, collection_name, **kwargs):
        message = kwargs
        message.update({'collection_name': collection_name})

        if collection_name in self.resources.keys():
            result = yield from self.on_message(**message)
        else:
            try:
                node_id = self.resources_directory[collection_name]
            except KeyError:
                raise UnknownService("Unknown service {0}".format(collection_name))

            result = yield from super().send(node_id, message)

        if result['success'] is False:
            raise ResourceException(result.pop("data"))

        return result.pop("data")


class ResourceService(BaseResourceService):

    def service_info(self):
        return {'name': self.name, 'resources': list(self.resources.keys()),
                'node_type': 'node'}

    def on_registration_message_worker(self, node_info):
        for resource_type in node_info['resources']:
            if resource_type in self.resources.keys():
                resources_workers = self.resources_worker_directory.setdefault(
                    resource_type, {})
                # TODO, change medium node_id ?
                resources_workers[node_info['name']] = node_info

        self.medium.send_registration_answer(node_info['node_id'])
        self.on_peer_join(node_info['node_id'])

    @asyncio.coroutine
    def on_message(self, collection_name, message_type=None, *args, **kwargs):
        '''Ignore message_type for the moment
        '''

        # Get collection
        try:
            collection = self.resources[collection_name]
        except KeyError:
            error_message = 'No collection named %s' % collection
            return {'success': False, 'message': error_message}

        self.logger.debug("Collection {0}".format(collection))

        # Try to get a result
        try:
            result = yield from collection.on_message(*args, **kwargs)
        except Exception as e:
            self.logger.exception("Error: {0}".format(str(e)))
            return {'success': False, 'data': str(e)}
        else:
            self.logger.debug("Success: {0}".format(result))
            return {'success': True, 'data': result}

    @asyncio.coroutine
    def publish(self, *args):
        '''Call BaseService.publish and call on_event on self.
        '''
        yield from super(ResourceService, self).publish(*args)

        # Publish to itself
        yield from self.on_event(*args)

    ### Utils
    def register_resource(self, collection):
        assert isinstance(collection, ResourceCollection)

        # Add self reference to collection
        collection.service = self

        # Resources collections
        self.resources[collection.resource_name] = collection

    def get_known_worker_nodes(self):
        return {resource_type: list(workers.keys()) for resource_type, workers in
                self.resources_worker_directory.items()}


class RealtimeResourceService(ResourceService):
    '''A subclass resource service compatible with realtime sockjs http
    interface.
    '''

    def on_event(self, message_type, data):
        # Test if someone is connected to the socks endpoint
        if not self.application.clients:
            return

        self.logger.info("On event %s", locals())
        self.application.clients[0].publishToRoom('*', 'event', data)

        topics = accumulate(message_type.split('.'), lambda x, y: '.'.join((x, y)))

        for topic in topics:
            self.logger.info('Publish %s to %s topic', data, topic)
            self.application.clients[0].publishToRoom(topic, 'event', data)


class ResourceCollection(object):

    resource_name = None
    resource_class = None
    service = None

    def __init__(self, resource_name):
        self.resource_name = resource_name
        self.logger = logging.getLogger("{0}.{1}".format(resource_name, 'collection'))

    def on_message(self, action, resource_id=None, **kwargs):
        if resource_id:
            resource = self.instantiate(resource_id=resource_id)
            self.logger.debug("Resource_id, then using resource {0}".format(resource))
            action_handler = getattr(resource, action, None)
        else:
            self.logger.debug("No resource id, then using collection {0}".format(self))
            action_handler = getattr(self, action, None)

        self.logger.debug("Action handler {0} {1}".format(action_handler, locals()))

        if action_handler and getattr(action_handler, 'is_callable', False):
            return action_handler(**kwargs)
        else:
            raise NoActionHandler('No handler for action {0}'.format(action))

    def instantiate(self, **kwargs):
        return self.resource_class(service=self.service,
            resource_collection=self, **kwargs)

    def publish(self, topic, message):
        message.update({'resource_name': self.resource_name})
        topic = '.'.join((self.resource_name, topic))
        yield from self.service.publish(topic, message)

    @is_callable
    def list(self, where=None):
        pass


class Resource(object):

    __metaclass__ = ABCMeta

    def __init__(self, resource_id, service, resource_collection):
        self.resource_id = resource_id
        self.service = service
        self.resource_collection = resource_collection

    @abstractmethod
    @is_callable
    def get(self):
        pass

    @abstractmethod
    @is_callable
    def create(self, resource_data):
        return self

    @abstractmethod
    @is_callable
    def patch(self, patch):
        pass

    @abstractmethod
    @is_callable
    def delete(self):
        pass

    @abstractmethod
    @is_callable
    def add_link(self, relation, target_id, title):
        pass

    def publish(self, topic, message):
        message.update({'resource_id': self.resource_id})
        topic = '.'.join((topic, self.resource_id))
        yield from self.resource_collection.publish(topic, message)


class ResourceWorker(BaseResourceService):

    def __init__(self, name, medium):
        name = '{:s}-{:s}'.format(name, str(uuid4()))
        self.rules = {}
        super().__init__(name, medium)

    @asyncio.coroutine
    def start(self):
        self.medium.periodic_call(self.poll_check, 10)
        yield from super().start()

    @asyncio.coroutine
    def poll_check(self):
        # Ask about existing resources matching rule
        self.logger.info('Poll check starting')
        for resource_type, rules in self.rules.items():
            for rule in rules:
                matching_resources = yield from self.send(collection_name=resource_type,
                                                          action="list",
                                                          where=rule.matcher)
                self.logger.info('Rule %s, resources %s', rule, matching_resources)
                for resource in matching_resources:
                    yield from rule(resource_type, resource['resource_data'],
                                    resource['resource_id'], 'periodic')

    def service_info(self):
        return {'name': self.name, 'resources': list(self.rules.keys()),
                'node_type': 'worker'}

    @asyncio.coroutine
    def on_event(self, message_type, resource_name, action, resource_id,
                 resource_data=None, **kwargs):

        # Check resource rules
        resource_rules = self.rules.get(resource_name, ())

        if not resource_rules:
            return

        if not resource_data and action != "delete":
            resource = yield from self.send(collection_name=resource_name,
                                            action="get",
                                            resource_id=resource_id)
            resource_data = resource['resource_data']

        # See if one rule match
        for rule in resource_rules:
            if rule.match(resource_data):
                yield from rule(resource_name, resource_data, resource_id, action)

    def register(self, callback, resource_type, **matcher):
        rule = Rule(callback, matcher)
        self.rules.setdefault(resource_type, []).append(rule)

        # Register to events matching resource_type
        self.medium.subscribe(resource_type)


class Rule(object):

    """Util class for matching events

    >>> from mock import Mock, sentinel
    >>> resource = {'foo': 'bar'}
    >>> callback = Mock(return_value=sentinel.RETURN)
    >>> rule = Rule(callback, {'foo': 'bar'})
    >>> rule.match({'foo': 'not_bar'})
    False
    >>> rule.match(resource)
    True
    >>> rule('Resource', resource, 'ResourceID')
    sentinel.RETURN
    >>> rule.callback.assert_called_once_with('Resource', resource, \
            'ResourceID')
    """

    def __init__(self, callback, matcher):
        self.callback = callback
        self.matcher = matcher

    def match(self, resource):
        return match(self.matcher, resource)

    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)

    def __repr__(self):
        return 'Rule({})'.format(self.__dict__)


#### Exceptions


class NoActionHandler(Exception):
    pass
