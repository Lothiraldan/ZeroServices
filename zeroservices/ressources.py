from .service import BaseService
from .exceptions import UnknownService, RessourceException
from .query import match
from abc import ABCMeta, abstractmethod
from uuid import uuid4

import logging


### Utils


def is_callable(method):
    method.is_callable = True
    return method


class RessourceService(BaseService):

    def __init__(self, name, medium):
        self.ressources = {}
        self.ressources_directory = {}
        self.ressources_worker_directory = {}
        super(RessourceService, self).__init__(name, medium)

    def service_info(self):
        return {'name': self.name, 'ressources': self.ressources.keys(),
                'node_type': 'node'}

    def save_new_node_info(self, node_info):
        super(RessourceService, self).save_new_node_info(node_info)

        for ressource in node_info.get('ressources', ()):
            self.ressources_directory[ressource] = node_info['node_id']

    def on_registration_message_worker(self, node_info):
        for ressource_type in node_info['ressources']:
            if ressource_type in self.ressources.keys():
                ressources_workers = self.ressources_worker_directory.setdefault(
                    ressource_type, {})
                # TODO, change medium node_id ?
                ressources_workers[node_info['name']] = node_info

        self.medium.send_registration_answer(node_info)
        self.on_peer_join(node_info)

    def on_message(self, collection, message_type=None, *args, **kwargs):
        '''Ignore message_type for the moment
        '''

        # Get collection
        try:
            collection = self.ressources[collection]
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

    def send(self, collection, **kwargs):
        message = kwargs
        message.update({'collection': collection})

        if collection in self.ressources.keys():
            return self.on_message(**message)

        try:
            node_id = self.ressources_directory[collection]
        except KeyError:
            raise UnknownService("Unknown service {0}".format(collection))

        result = super(RessourceService, self).send(node_id, message)

        if result['success'] == False:
            raise RessourceException(result.pop("data"))

        return result.pop("data")

    ### Utils
    def register_ressource(self, collection):
        assert isinstance(collection, RessourceCollection)

        # Add self reference to collection
        collection.service = self

        # Ressources collections
        self.ressources[collection.ressource_name] = collection

    def get_known_worker_nodes(self):
        return {ressource_type: list(workers.keys()) for ressource_type, workers in
                self.ressources_worker_directory.items()}


class RessourceCollection(object):

    ressource_name = None
    ressource_class = None
    service = None

    def __init__(self, ressource_class, ressource_name):
        self.ressource_class = ressource_class
        self.ressource_name = ressource_name
        self.logger = logging.getLogger("{0}.{1}".format(ressource_name, 'collection'))

    def on_message(self, action, ressource_id=None, **kwargs):
        if ressource_id:
            ressource = self.instantiate(ressource_id=ressource_id)
            action_handler = getattr(ressource, action, None)
        else:
            action_handler = getattr(self, action, None)

        self.logger.debug("Action handler {0}".format(action_handler))

        if action_handler and getattr(action_handler, 'is_callable', False):
            return action_handler(**kwargs)
        else:
            raise NoActionHandler('No handler for action %s' % action)

    def instantiate(self, **kwargs):
        return self.ressource_class(service=self.service,
            ressource_collection=self, **kwargs)

    def publish(self, message):
        message.update({'ressource_name': self.ressource_name})
        self.service.publish(self.ressource_name, message)

    @is_callable
    def list(self, where=None):
        pass



class Ressource(object):

    __metaclass__ = ABCMeta

    def __init__(self, ressource_id, service, ressource_collection):
        self.ressource_id = ressource_id
        self.service = service
        self.ressource_collection = ressource_collection

    @abstractmethod
    @is_callable
    def get(self):
        pass

    @abstractmethod
    @is_callable
    def create(self, ressource_data):
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

    def publish(self, message):
        message.update({'ressource_id': self.ressource_id})
        self.ressource_collection.publish(message)


class RessourceWorker(BaseService):

    def __init__(self, name, medium):
        name = '{:s}-{:s}'.format(name, str(uuid4()))
        self.rules = {}
        super(RessourceWorker, self).__init__(name, medium)

    def service_info(self):
        return {'name': self.name, 'ressources': self.rules.keys(),
                'node_type': 'worker'}

    def on_event(self, message_type, message):
        ressource_name = message['ressource_name']
        ressource_data = message.get('ressource_data')
        action = message['action']
        ressource_id = message['ressource_id']

        # See if one rule match
        for rule in self.rules.get(ressource_name, ()):
            if rule.match(ressource_data):
                rule(ressource_name, ressource_data, ressource_id, action)

    def register(self, callback, ressource_type, **matcher):
        rule = Rule(callback, matcher)
        self.rules.setdefault(ressource_type, []).append(rule)

        # Register to events matching ressource_type
        self.medium.subscribe(ressource_type)


class Rule(object):

    """Util class for matching events

    >>> from mock import Mock, sentinel
    >>> ressource = {'foo': 'bar'}
    >>> callback = Mock(return_value=sentinel.RETURN)
    >>> rule = Rule(callback, {'foo': 'bar'})
    >>> rule.match({'foo': 'not_bar'})
    False
    >>> rule.match(ressource)
    True
    >>> rule('Ressource', ressource, 'RessourceID')
    sentinel.RETURN
    >>> rule.callback.assert_called_once_with('Ressource', ressource, \
            'RessourceID')
    """

    def __init__(self, callback, matcher):
        self.callback = callback
        self.matcher = matcher

    def match(self, ressource):
        return match(self.matcher, ressource)

    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)

    def __repr__(self):
        return 'Rule({})'.format(self.__dict__)


#### Exceptions


class NoActionHandler(Exception):
    pass
