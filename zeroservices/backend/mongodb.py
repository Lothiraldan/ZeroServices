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
        document_data = {'_id': self.ressource_id}
        document_data.update(ressource_data)
        self.collection.insert(document_data)

        self.publish('create', {'action': 'create',
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

        self.publish('patch', {'action': 'patch', 'patch': patch})

        new_document.pop('_id')
        return new_document

    @is_callable
    def delete(self):
        self.collection.remove({'_id': self.ressource_id})
        self.publish('delete', {'action': 'delete'})
        return 'OK'

    @is_callable
    def add_link(self, relation, target_id, title):
        target_relation = target_id[0]
        patch = {"$push": {"_links.{}".format(relation):
                    {"target_id": target_id, "title": title}},
                 "$set": {"_links.latest.{}".format(target_relation):
                    target_id}}
        self.collection.find_and_modify({'_id': self.ressource_id}, patch,
                                        new=True)

        self.publish('add_link', {'action': 'add_link', 'target_id': target_id,
            'title': title, 'relation': relation})

        return "OK"

    @property
    def document(self):
        if self._document is None:
            self._document = self.collection.find_one({'_id': self.ressource_id})
        return self._document


class MongoDBCollection(RessourceCollection):

    def __init__(self, collection_name):
        super(MongoDBCollection, self).__init__(MongoDBRessource, collection_name)
        self.collection = pymongo.Connection()['SmartForge'][collection_name]

    def instantiate(self, **kwargs):
        return super(MongoDBCollection, self).instantiate(
            collection=self.collection, **kwargs)

    @is_callable
    def list(self, where=None):
        if where is None:
            where = {}
        result = list()
        for document in self.collection.find(where):
            result.append({'ressource_id': document.pop('_id'),
                           'ressource_data': document})
        return result
