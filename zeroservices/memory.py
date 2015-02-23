from .medium import BaseMedium
from .resources import (ResourceCollection, Resource,
                         is_callable)
from .exceptions import ServiceUnavailable
from .query import match


# Memory Collection


class MemoryResource(Resource):

    def __init__(self, collection, **kwargs):
        super(MemoryResource, self).__init__(**kwargs)
        self.collection = collection

    @is_callable
    def create(self, resource_data):
        self.collection[self.resource_id] = resource_data
        yield from self.publish('create', {'action': 'create', 'resource_data': resource_data})
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
        resource = self.collection[self.resource_id]

        set_keys = patch['$set']
        for key, value in set_keys.items():
            resource[key] = value

        yield from self.publish('patch', {'action': 'patch', 'patch': patch})

        return resource

    @is_callable
    def delete(self):
        del self.collection[self.resource_id]
        yield from self.publish('delete', {'action': 'delete'})
        return 'OK'

    @is_callable
    def add_link(self, relation, target_id, title):
        target_relation = target_id[0]
        resource = self.collection[self.resource_id]
        links = resource.setdefault('_links', {})
        links.setdefault(relation, []).append({'target_id': target_id,
                                               'title': title})
        links.setdefault('latest', {})[target_relation] = target_id

        event = {'action': 'add_link', 'target_id': target_id,
                 'title': title, 'relation': relation}
        yield from self.publish('add_link', event)
        return 'OK'


class MemoryCollection(ResourceCollection):

    resource_class = MemoryResource

    def __init__(self, collection_name):
        super(MemoryCollection, self).__init__(collection_name)
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
