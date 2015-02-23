import asyncio

from zeroservices.backend.mongodb import MongoDBCollection
from . import _BaseCollectionTestCase

from ..utils import TestCase, _create_test_resource_service, _async_test

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class MongoDBCollectionTestCase(_BaseCollectionTestCase):

    def setUp(self):
        super(MongoDBCollectionTestCase, self).setUp()
        self.database_name = 'test'
        self.collection = MongoDBCollection(self.resource_name,
                                            self.database_name)
        self.collection.service = self.service

    def tearDown(self):
        super().tearDown()
        self.collection.collection.drop()


class MongoDBTestCase(TestCase):

    def setUp(self):
        self.database_name = 'test'
        self.resource_name = 'test_resource'

        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

        self.service = _create_test_resource_service('test_service', self.loop)
        self.collection = MongoDBCollection(self.resource_name,
                                            database_name=self.database_name)
        self.collection.service = self.service

    def tearDown(self):
        self.collection.collection.drop()

    @_async_test
    def test_custom_database(self):
        # Create a resource
        resource_id = 'UUID1'
        message_args = {'resource_data': {'kwarg_1': 1, 'kwarg_2': 2},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        result = yield from self.collection.on_message(**query)
        self.assertEqual(result,
                         {'resource_id': 'UUID1'})

        # Check that resource exists
        resource_list = yield from self.collection.on_message(action='list')
        self.assertEqual(resource_list,
                         [message_args])

        # On a separate database, check that resource doesn't exists
        collection2 = MongoDBCollection(self.resource_name,
                                        database_name='other')

        resource_list = yield from collection2.on_message(action='list')
        self.assertEqual(resource_list, [])
