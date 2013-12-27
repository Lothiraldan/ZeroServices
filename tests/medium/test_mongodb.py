import unittest

from zeroservices.backend.mongodb import MongoDBCollection
from zeroservices import BaseService
from mock import Mock
from ..utils import test_medium


class MongoDBCollectionTestCase(unittest.TestCase):

    def setUp(self):
        self.service = Mock(spec_set=BaseService)
        self.service.medium = test_medium()

        self.ressource_name = 'test_mongodb'
        self.collection = MongoDBCollection(self.ressource_name)
        self.collection.service = self.service

        # Ressource
        self.ressource_id = 'UUID-1'
        self.ressource_data = {'field1': 1, 'field2': 2}

    def tearDown(self):
        self.collection.collection.drop()

    def test_create(self):
        message = {'action': 'create', 'ressource_id': self.ressource_id,
                   'ressource_data': self.ressource_data}

        self.assertEqual(self.collection.on_message(**message),
                         {'ressource_id': self.ressource_id})

    def test_get(self):
        self.test_create()

        message = {'action': 'get', 'ressource_id': self.ressource_id}

        self.assertEqual(self.collection.on_message(**message),
                         {'ressource_id': self.ressource_id,
                          'ressource_data': self.ressource_data})

    def test_update(self):
        self.test_create()

        patch = {'field3': 3, 'field4': 4}
        query = {'$set': patch}

        message = {'action': 'patch', 'ressource_id': self.ressource_id,
                   'patch': query}

        expected_document = self.ressource_data.copy()
        expected_document.update(patch)
        expected_document['_id'] = self.ressource_id

        self.assertEqual(self.collection.on_message(**message),
            expected_document)
