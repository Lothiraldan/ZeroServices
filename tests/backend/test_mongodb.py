from unittest import TestCase
from zeroservices.backend.mongodb import MongoDBCollection
from zeroservices.resources import ResourceService
from zeroservices.memory import MemoryMedium
from . import _BaseCollectionTestCase


class MongoDBCollectionTestCase(_BaseCollectionTestCase):

    def setUp(self):
        super(MongoDBCollectionTestCase, self).setUp()
        self.database_name = 'test'
        self.collection = MongoDBCollection(self.resource_name,
                                            self.database_name)
        self.collection.service = self.service

    def tearDown(self):
        self.collection.collection.drop()


class MongoDBTestCase(TestCase):

    def setUp(self):
        self.database_name = 'test'
        self.resource_name = 'test_resource'

        self.medium = MemoryMedium('test_medium')
        self.service = ResourceService('test_mongodb', self.medium)
        self.collection = MongoDBCollection(self.resource_name,
                                            database_name=self.database_name)
        self.service.register_resource(self.collection)

    def tearDown(self):
        self.collection.collection.drop()

    def test_custom_database(self):
        # Create a resource
        resource_id = 'UUID1'
        message_args = {'resource_data': {'kwarg_1': 1, 'kwarg_2': 2},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.assertEqual(self.collection.on_message(**query),
                         {'resource_id': 'UUID1'})

        # Check that resource exists
        self.assertEqual(self.collection.on_message(action='list'),
                         [message_args])

        # On a separate database, check that resource doesn't exists
        medium2 = MemoryMedium('test_medium2')
        service2 = ResourceService('test_mongodb2', medium2)
        collection2 = MongoDBCollection(self.resource_name,
                                        database_name='other')
        service2.register_resource(collection2)

        self.assertEqual(collection2.on_message(action='list'), [])

