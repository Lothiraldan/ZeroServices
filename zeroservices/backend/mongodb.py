import sys
import pymongo
from bson import ObjectId
import os

from copy import copy

from zeroservices import ResourceCollection, Resource
from zeroservices.resources import is_callable


class MongoDBResource(Resource):

    def __init__(self, collection, **kwargs):
        super(MongoDBResource, self).__init__(**kwargs)
        self.collection = collection
        self._document = None

    @is_callable
    def create(self, resource_data):
        document_data = {'_id': self.resource_id}
        document_data.update(resource_data)
        self.collection.insert(document_data)

        yield from self.publish('create', {'action': 'create',
                                'resource_data': resource_data})

        return {'resource_id': self.resource_id}

    @is_callable
    def get(self):
        document = self.document

        if not document:
            return 'NOK'

        return {'resource_id': str(document.pop('_id')),
                'resource_data': document}

    @is_callable
    def patch(self, patch):
        new_document = self.collection.find_and_modify({'_id': ObjectId(self.resource_id)},
            patch, new=True)

        yield from self.publish('patch', {'action': 'patch', 'patch': patch})

        new_document.pop('_id')
        return new_document

    @is_callable
    def delete(self):
        self.collection.remove({'_id': self.resource_id})
        yield from self.publish('delete', {'action': 'delete'})
        return 'OK'

    @is_callable
    def add_link(self, relation, target_id, title):
        target_relation = target_id[0]
        patch = {"$push": {"_links.{}".format(relation):
                    {"target_id": target_id, "title": title}},
                 "$set": {"_links.latest.{}".format(target_relation):
                    target_id}}
        self.collection.find_and_modify({'_id': self.resource_id}, patch,
                                        new=True)

        event = {'action': 'add_link', 'target_id': target_id,
                 'title': title, 'relation': relation}
        yield from self.publish('add_link', event)

        return "OK"

    @property
    def document(self):
        if self._document is None:
            self._document = self.collection.find_one({'_id': ObjectId(self.resource_id)})
        return self._document


class MongoDBCollection(ResourceCollection):

    resource_class = MongoDBResource

    def __init__(self, collection_name, database_name):
        super(MongoDBCollection, self).__init__(collection_name)
        self.database_name = database_name
        self.collection_name = collection_name

        mongo_host = os.environ.get('MONGO_HOST', 'localhost')

        self.connection = pymongo.MongoClient(host=mongo_host)
        self.database = self.connection[database_name]
        self.collection = self.database[collection_name]

    def instantiate(self, **kwargs):
        return super(MongoDBCollection, self).instantiate(
            collection=self.collection, **kwargs)

    @is_callable
    def list(self, where=None):
        if where is None:
            where = {}

        # Support for fulltext-search
        if 'text' in where:
            text = where.pop('text')
            where['$text'] = {'$search': text}

        result = list()
        for document in self.collection.find(where):
            result.append({'resource_id': str(document.pop('_id')),
                           'resource_data': document})
        return result

    @is_callable
    def create(self, resource_data):
        document_data = copy(resource_data)
        document_id = self.collection.insert(document_data)
        # Replace ObjectId by a str
        document_data['_id'] = str(document_data['_id'])

        yield from self.publish('create', {'action': 'create',
                                'resource_data': document_data,
                                'resource_id': str(document_id)})

        return {'resource_id': str(document_id)}
