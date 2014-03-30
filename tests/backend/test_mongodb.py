import unittest

from zeroservices.backend.mongodb import MongoDBCollection
from zeroservices import BaseService
from ..utils import test_medium

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


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

    def _create(self, ressource_data, ressource_id):
        message = {'action': 'create', 'ressource_id': ressource_id,
                   'ressource_data': ressource_data}
        self.collection.on_message(**message)

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

    def test_delete(self):
        self.test_get()

        message = {'action': 'delete', 'ressource_id': self.ressource_id}

        self.assertEqual(self.collection.on_message(**message),
                         'OK')


        message = {'action': 'get', 'ressource_id': self.ressource_id}

        self.assertEqual(self.collection.on_message(**message),
                         'NOK')

    def test_add_link(self):
        self.test_create()

        relation = 'relation_type'
        target_id = 'target'
        title = 'title'
        message = {'action': 'add_link', 'ressource_id': self.ressource_id,
                   'relation': relation, 'target_id': target_id, 'title': title}
        self.assertEqual(self.collection.on_message(**message),
            "OK")

        expected_data = self.ressource_data.copy()
        expected_data.update({'_links': {relation: [
                            {"target_id": target_id, "title": title}]}})
        expected_document = {'ressource_id': self.ressource_id,
                             'ressource_data': expected_data}

        message = {'action': 'get', 'ressource_id': self.ressource_id}
        self.assertEqual(self.collection.on_message(**message),
                         expected_document)

    def test_list(self):
        message = {'action': 'list'}

        # Check that list doesn't return anything
        self.assertEqual(self.collection.on_message(**message),
                         [])

        # Create a doc
        self.test_create()

        # Check that list return the document
        self.assertEqual(self.collection.on_message(**message),
                         [{'ressource_id': self.ressource_id,
                          'ressource_data': self.ressource_data}])

    def test_list_filter(self):
        doc_1 = ({'field1': 1, 'field2': 2}, 'UUID-1')
        doc_2 = ({'field1': 3, 'field2': 2}, 'UUID-2')
        doc_3 = ({'field1': 1, 'field2': 4}, 'UUID-3')
        docs = (doc_1, doc_2, doc_3)

        for doc in docs:
            self._create(*doc)

        # All docs
        message = {'action': 'list'}
        expected = [{'ressource_id': x[1], 'ressource_data': x[0]} for x in docs]
        self.assertEqual(self.collection.on_message(**message),
                         expected)

        # Field1 = 1
        message = {'action': 'list', 'where': {'field1': 1}}
        expected = [{'ressource_id': x[1], 'ressource_data': x[0]} for x in docs if x[0]['field1'] == 1]
        self.assertEqual(self.collection.on_message(**message),
                         expected)

        # Field1 = 3
        message = {'action': 'list', 'where': {'field1': 3}}
        expected = [{'ressource_id': x[1], 'ressource_data': x[0]} for x in docs if x[0]['field1'] == 3]
        self.assertEqual(self.collection.on_message(**message),
                         expected)

        # Field2 = 2
        message = {'action': 'list', 'where': {'field2': 2}}
        expected = [{'ressource_id': x[1], 'ressource_data': x[0]} for x in docs if x[0]['field2'] == 2]
        self.assertEqual(self.collection.on_message(**message),
                         expected)
