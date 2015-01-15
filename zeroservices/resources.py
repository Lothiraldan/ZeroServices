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
    return method


def dynamic_attribute(*dependencies):
    def wrapper(func):
        func.dependencies = dependencies
        return func
    return wrapper


class BaseResourceService(BaseService):

    application = None

    def __init__(self, name, medium):
        self.resources = {}
        self.resources_directory = {}
        self.resources_worker_directory = {}
        super(BaseResourceService, self).__init__(name, medium)

    def save_new_node_info(self, node_info):
        super(BaseResourceService, self).save_new_node_info(node_info)

        for resource in node_info.get('resources', ()):
            self.resources_directory[resource] = node_info['node_id']

    def send(self, collection, **kwargs):
        message = kwargs
        message.update({'collection': collection})

        if collection in self.resources.keys():
            result = self.on_message(**message)
        else:
            try:
                node_id = self.resources_directory[collection]
            except KeyError:
                raise UnknownService("Unknown service {0}".format(collection))

            result = super(BaseResourceService, self).send(node_id, message)

        if result['success'] is False:
            raise ResourceException(result.pop("data"))

        return result.pop("data")


class ResourceService(BaseResourceService):

    def service_info(self):
        return {'name': self.name, 'resources': self.resources.keys(),
                'node_type': 'node'}

    def on_registration_message_worker(self, node_info):
        for resource_type in node_info['resources']:
            if resource_type in self.resources.keys():
                resources_workers = self.resources_worker_directory.setdefault(
                    resource_type, {})
                # TODO, change medium node_id ?
                resources_workers[node_info['name']] = node_info

        self.medium.send_registration_answer(node_info)
        self.on_peer_join(node_info)

    def on_message(self, collection, message_type=None, *args, **kwargs):
        '''Ignore message_type for the moment
        '''

        # Get collection
        try:
            collection = self.resources[collection]
        except KeyError:
            error_message = 'No collection named %s' % collection
            return {'success': False, 'message': error_message}

        self.logger.debug("Collection {0}".format(collection))

        # Try to get a result
        try:
            result = collection.on_message(*args, **kwargs)
        except Exception as e:
            self.logger.exception("Error: {0}".format(str(e)))
            return {'success': False, 'data': str(e)}
        else:
            self.logger.debug("Success: {0}".format(result))
            return {'success': True, 'data': result}

    def publish(self, *args):
        '''Call BaseService.publish and call on_event on self.
        '''
        super(ResourceService, self).publish(*args)

        # Publish to itself
        self.on_event(*args)

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
        self.logger.info("On event %s", locals())
        self.application.clients[0].publishToRoom('*', 'event', data)

        topics = accumulate(message_type.split('.'), lambda x, y: '.'.join((x, y)))

        for topic in topics:
            self.application.clients[0].publishToRoom(topic, 'event', data)


class ResourceCollection(object):

    resource_name = None
    resource_class = None
    service = None

    def __init__(self, resource_class, resource_name):
        self.resource_class = resource_class
        self.resource_name = resource_name
        self.logger = logging.getLogger("{0}.{1}".format(resource_name, 'collection'))

    def on_message(self, action, resource_id=None, **kwargs):
        if resource_id:
            resource = self.instantiate(resource_id=resource_id)
            action_handler = getattr(resource, action, None)
        else:
            action_handler = getattr(self, action, None)

        self.logger.debug("Action handler {0}".format(action_handler))

        if action_handler and getattr(action_handler, 'is_callable', False):
            return action_handler(**kwargs)
        else:
            raise NoActionHandler('No handler for action %s' % action)

    def instantiate(self, **kwargs):
        return self.resource_class(service=self.service,
            resource_collection=self, **kwargs)

    def publish(self, topic, message):
        message.update({'resource_name': self.resource_name})
        self.service.publish('.'.join((self.resource_name, topic)), message)

    @is_callable
    def list(self, where=None):
        pass


class Resource(object):

    __metaclass__ = ABCMeta
    dynamic_attributes = []

    def __init__(self, resource_id, service, resource_collection):
        self.resource_id = resource_id
        self.service = service
        self.resource_collection = resource_collection

        self.dynamic_attributes_map = {}

        for dynamic_attribute in self.dynamic_attributes:
            dynamic_attribute_method = getattr(self, dynamic_attribute)
            self.dynamic_attributes_map[dynamic_attribute] = (dynamic_attribute_method, dynamic_attribute_method.dependencies)

    @abstractmethod
    @is_callable
    def get(self):
        pass

    @abstractmethod
    @is_callable
    def create(self, resource_data):
        # Iterate on dynamic attributes
        for dynamic_attribute, meta in self.dynamic_attributes_map.items():
            method_args = {key: resource_data[key] for key in meta[1]}
            resource_data[dynamic_attribute] = meta[0](**method_args)
        return resource_data

    @abstractmethod
    @is_callable
    def patch(self, patch):
        # Iterate on dynamic attributes
        patch_keys = patch['$set'].keys()
        for key in patch_keys:
            for dynamic_attribute, meta in self.dynamic_attributes_map.items():
                if key in meta[1]:
                    if not all(require in patch['$set'] for require in meta[1]):
                        document = self.get()['resource_data']
                        method_args = {key: patch['$set'].get(key, document[key]) for key in meta[1]}
                        patch['$set'][dynamic_attribute] = meta[0](**method_args)
                    else:
                        method_args = {key: patch['$set'][key] for key in meta[1]}
                        patch['$set'][dynamic_attribute] = meta[0](**method_args)
        return patch

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
        self.resource_collection.publish('.'.join((topic, self.resource_id)),
                                          message)


class ResourceWorker(BaseResourceService):

    def __init__(self, name, medium):
        name = '{:s}-{:s}'.format(name, str(uuid4()))
        self.rules = {}
        super(ResourceWorker, self).__init__(name, medium)

    def main(self):
        self.medium.periodic_call(self.poll_check, 10)
        super(ResourceWorker, self).main()

    def poll_check(self):
        # Ask about existing resources matching rule
        self.logger.info('Poll check starting')
        for resource_type, rules in self.rules.items():
            for rule in rules:
                matching_resources = self.send(collection=resource_type,
                                                action="list",
                                                where=rule.matcher)
                self.logger.info('Rule %s, resources %s', rule, matching_resources)
                for resource in matching_resources:
                    rule(resource_type, resource['resource_data'],
                         resource['resource_id'], 'periodic')

    def service_info(self):
        return {'name': self.name, 'resources': self.rules.keys(),
                'node_type': 'worker'}

    def on_event(self, message_type, message):
        resource_name = message['resource_name']

        # Check resource rules
        resource_rules = self.rules.get(resource_name, ())

        if not resource_rules:
            return

        resource_data = message.get('resource_data')
        action = message['action']
        resource_id = message['resource_id']

        if not resource_data and action != "delete":
            resource = self.send(collection=resource_name,
                                  action="get",
                                  resource_id=resource_id)
            resource_data = resource['resource_data']

        # See if one rule match
        for rule in resource_rules:
            if rule.match(resource_data):
                rule(resource_name, resource_data, resource_id, action)

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
