from .service import BaseService
from abc import ABCMeta, abstractmethod

class RessourceService(BaseService):

    def __init__(self, name, medium):
        super(RessourceService, self).__init__(name, medium)
        self.ressources = {}
        self.ressources_directory = {}

    def service_info(self):
        return {'name': self.name, 'ressources': self.ressources.keys()}

    def save_new_node_info(self, node_info):
        super(RessourceService, self).save_new_node_info(node_info)

        for ressource in node_info.get('ressources', ()):
            self.ressources_directory[ressource] = node_info['node_id']

    def on_message(self, collection, *args, **kwargs):
        # Get collection
        try:
            collection = self.ressources[collection]
        except KeyError:
            error_message = 'No collection named %s' % collection
            return {'success': False, 'message': error_message}

        # Try to get a result
        try:
            result = collection.on_message(*args, **kwargs)
        except Exception as e:
            return {'success': False, 'data': str(e)}
        else:
            return {'success': True, 'data': result}

    ### Utils
    def register_ressource(self, collection):
        assert isinstance(collection, RessourceCollection)

        # Add self reference to collection
        collection.service = self

        # Ressources collections
        self.ressources[collection.ressource_name] = collection


class RessourceCollection(object):

    ressource_name = None
    ressource_class = None
    service = None

    def on_message(self, action, **kwargs):
        action_handler = getattr(self, action, None)
        if action_handler:
            return action_handler(**kwargs)
        else:
            raise NoActionHandler('No handler for action %s' % action)

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


#### Exceptions


class NoActionHandler(Exception):
    pass
