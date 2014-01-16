import sys
import pymongo

from zeroservices import RessourceCollection, Ressource
from zeroservices.ressources import is_callable

class MongoDBRessource(Ressource):

    def __init__(self, collection, **kwargs):
        super(MongoDBRessource, self).__init__(**kwargs)
        self.collection = collection
        self._document = None

    @is_callable
    def create(self, ressource_data):
        self.document_data = {'_id': self.ressource_id}
        self.document_data.update(ressource_data)
        self.collection.insert(self.document_data)

        self.service.medium.publish(self.ressource_collection.ressource_name,
            {'type': 'new', '_id': self.ressource_id,
             'ressource_data': ressource_data})

        return {'ressource_id': self.ressource_id}

    @is_callable
    def get(self):
        document = self.document

        if not document:
            return 'NOK'

        return {'ressource_id': document.pop('_id'),
                'ressource_data': document}

    @is_callable
    def patch(self, patch):
        new_document = self.collection.find_and_modify({'_id': self.ressource_id},
            patch, new=True)
        return new_document

    @is_callable
    def delete(self):
        self.collection.remove({'_id': self.ressource_id})
        return 'OK'

    @is_callable
    def add_link(self, relation, target_id, title):
        patch = {"$push": {"_links.%s" % relation:
                    {"target_id": target_id, "title": title}}}
        self.collection.find_and_modify({'_id': self.ressource_id}, patch,
                                        new=True)

        self.service.medium.publish(self.ressource_collection.ressource_name,
            {'type': 'new_link', '_id': self.ressource_id,
            'target_id': target_id, 'title': title})

        return "OK"

    @property
    def document(self):
        if self._document is None:
            self._document = self.collection.find_one({'_id': self.ressource_id})
        return self._document

class MongoDBCollection(RessourceCollection):

    def __init__(self, collection_name):
        self.collection = pymongo.Connection()['SmartForge'][collection_name]
        self.ressource_class = MongoDBRessource
        self.ressource_name = collection_name

    def instantiate(self, **kwargs):
        return super(MongoDBCollection, self).instantiate(
            collection=self.collection, **kwargs)

    @is_callable
    def list(self, where=None):
        if where is None:
            where = {}
        return list(self.collection.find(where))
