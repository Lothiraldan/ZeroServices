import sys
import json
import logging
import traceback

from copy import copy
from abc import ABCMeta, abstractmethod
from tornado import gen

from zeroservices.medium.zeromq import ZeroMQMedium
from zeroservices.utils import maybe_asynchronous

logging.basicConfig(level=logging.DEBUG)

DEFAULT_MEDIUM = ZeroMQMedium


class BaseService(object):

    medium = None
    nodes_directory = {}

    def __init__(self, name, medium):
        self.name = name
        self.medium = medium
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
        self.medium.send(self.nodes_directory[node_id], message, **kwargs)

    def publish(self, *args):
        self.medium.publish(*args)

    def main(self):
        self.medium.register()
        self.medium.start()

    def close(self):
        self.medium.close()


class RessourceService(BaseService):
    name = None
    ressources = []

    def __init__(self, name, medium):
        super(RessourceService, self).__init__(name, medium)
        self.ressources_directory = {}

    def service_info(self):
        return {'name': self.name, 'ressources': self.ressources}

    def save_new_node_info(self, node_info):
        super(RessourceService, self).save_new_node_info(node_info)

        for ressource in node_info.get('ressources', ()):
            self.ressources_directory[ressource] = node_info['node_id']

    @gen.engine
    def process_query(self, collection, action, args={}, ressource_id=None,
            callback=None):
        self.logger.info("Query: %s.%s(%s)" % (collection, action, args))

        try:
            rcollection = self.ressources_collections[collection]

            rcollection.service = self

            if ressource_id:
                ressource = rcollection.get(ressource_id)
                service_callback = getattr(ressource, action)
            else:
                service_callback = getattr(rcollection, action)
            self.logger.info("Call %s with args %s", service_callback, args)
            result = yield gen.Task(service_callback, **args)

            try:
                success = result[0]
                if isinstance(success, bool):
                    data = result[1] if len(result[1:]) == 1 else result[1:]
                else:
                    success, data = True, result
            except (TypeError, KeyError, IndexError):
                success, data = True, result

            self.logger.info('Result %s' % {'success': success, 'data': data})
            callback({'success': success, 'data': data})
        except AttributeError as e:
            callback({'success': False,
                'data': 'The service can not satisfy the query: %s' % e})
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            callback({'success': False,
                'message': 'Internal error: %s' % repr(e)})

    # Process raw event
    def process_event(self, message_type, data):
        self.logger.debug('Get message %s: %s', message_type, data)

    ### Getters / Setters

    def query_get_links(self, ressource_id):
        raise NotImplementedError()

    def query_add_links(self, ressource_id, link_id):
        raise NotImplementedError()

    def query_get_details(self, ressource_id):
        raise NotImplementedError()

    def query_update(self, ressource_id, data):
        raise NotImplementedError()

    ### Utils
    @classmethod
    def register(cls, collection):
        assert isinstance(collection, RessourceCollection)

        # Add self reference to collection
        collection.service = cls

        # Ressources collections
        ressources_collections = copy(cls.ressources_collections)
        ressources_collections[collection.ressource_name] = collection
        cls.ressources_collections = ressources_collections

        #Ressources
        ressources = cls.ressources[:]
        ressources.append(collection.ressource_name)
        cls.ressources = ressources

    def call(self, collection, **kwargs):
        self.logger.info("Call %s with %s" % (collection, kwargs))
        return self.medium.call(collection, **kwargs)

    def publish(self, etype, event):
        self.medium.publish(etype, event)

    def _register_info(self):
        return {'name': self.name, 'ressources': self.ressources}



class RessourceCollection(object):

    __metaclass__ = ABCMeta
    ressource_name = None
    ressource_class = None

    @maybe_asynchronous
    def create(self, ressource_id, ressource_data=None, **kwargs):
        if kwargs:
            raise Exception(kwargs)

        if ressource_data is None:
            ressource_data = {}

        if self.ressource_class:
            ressource = self.instantiate(ressource_id=ressource_id)
            ressource.create(ressource_data)
            return ressource.get()

    def instantiate(self, **kwargs):
        return self.ressource_class(service=self.service,
            ressource_collection=self, **kwargs)

    def get(self, ressource_id):
        return self.instantiate(ressource_id=ressource_id)

    @abstractmethod
    def list(self, where=None):
        pass


class Ressource(object):

    __metaclass__ = ABCMeta

    def __init__(self, ressource_id, service, ressource_collection):
        self.ressource_id = ressource_id
        self.service = service
        self.ressource_collection = ressource_collection

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def update(self, patch):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def add_link(self, relation, target_id, title):
        pass
