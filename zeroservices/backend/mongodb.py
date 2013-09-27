import sys
import pymongo

from smartforge.service import RessourceCollection, Ressource
from smartforge.utils import maybe_asynchronous

class MongoDBRessource(Ressource):

    def __init__(self, collection, **kwargs):
        super(MongoDBRessource, self).__init__(**kwargs)
        self.collection = collection
        self._document = None

    @property
    def document(self):
        if self._document is None:
            self._document = self.collection.find({'_id': self.ressource_id})
        return self._document

    @maybe_asynchronous
    def create(self, document):
        self.document_data = {'_id': self.ressource_id}
        self.document_data.update(document)
        self.collection.insert(self.document_data)

        self.service.medium.publish(self.ressource_collection.ressource_name,
            {'type': 'new', '_id': self.ressource_id, 'document': document})

        return {'_id': self.ressource_id}

    @maybe_asynchronous
    def get(self):
        return self.document

    @maybe_asynchronous
    def update(self, patch):
        pass

    @maybe_asynchronous
    def delete(self):
        pass

    @maybe_asynchronous
    def add_link(self, relation, target_id, title):
        self.get()
        links = self.document.setdefault("_links", {})
        relation_links = links.setdefault(relation, [])
        relation_links.append({"target_id": target_id, "title": title})
        self.collection.save(self.document)

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

    @maybe_asynchronous
    def list(self, where=None):
        if where is None:
            where = {}
        return list(self.collection.find(where))
