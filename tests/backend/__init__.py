from zeroservices import BaseService
from ..utils import test_medium, TestCase

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class _BaseCollectionTestCase(TestCase):

    def setUp(self):
        self.service = Mock(spec_set=BaseService)
        self.service.medium = test_medium()

        # Ressource
        self.ressource_id = 'UUID-1'
        self.ressource_data = {'field1': 1, 'field2': 2}
        self.ressource_name = 'test_collection'

        self.event_payload = {'ressource_id': self.ressource_id,
                              'ressource_name': self.ressource_name}

        self.maxDiff = None

    def _create(self, ressource_data, ressource_id):
        message = {'action': 'create', 'ressource_id': ressource_id,
                   'ressource_data': ressource_data}
        self.collection.on_message(**message)

    def test_create(self):
        message = {'action': 'create', 'ressource_id': self.ressource_id,
                   'ressource_data': self.ressource_data}

        self.assertEqual(self.collection.on_message(**message),
                         {'ressource_id': self.ressource_id})

        expected_payload = self.event_payload.copy()
        expected_payload.update({'action': 'create',
                                 'ressource_data': self.ressource_data})

        event_topic = '%s.create.%s' % (self.ressource_name, self.ressource_id)
        self.service.publish.assert_called_once_with(event_topic,
                                                     expected_payload)

        self.service.publish.reset_mock()

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

        self.assertEqual(self.collection.on_message(**message),
                         expected_document)

        message = {'action': 'get', 'ressource_id': self.ressource_id}

        self.assertEqual(self.collection.on_message(**message),
                         {'ressource_id': self.ressource_id,
                          'ressource_data': expected_document})

        expected_payload = self.event_payload.copy()
        expected_payload.update({'action': 'patch', 'patch': query})

        event_topic = '%s.patch.%s' % (self.ressource_name, self.ressource_id)
        self.service.publish.assert_called_once_with(event_topic,
                                                     expected_payload)

    def test_delete(self):
        self.test_create()

        message = {'action': 'delete', 'ressource_id': self.ressource_id}

        self.assertEqual(self.collection.on_message(**message),
                         'OK')

        message = {'action': 'get', 'ressource_id': self.ressource_id}

        self.assertEqual(self.collection.on_message(**message),
                         'NOK')

        expected_payload = self.event_payload.copy()
        expected_payload.update({'action': 'delete'})

        event_topic = '%s.delete.%s' % (self.ressource_name, self.ressource_id)
        self.service.publish.assert_called_once_with(event_topic,
                                                     expected_payload)

  # Add another link on same relation
    def test_add_link(self):
        self.test_create()

        relation = 'relation_type'
        target_id = ['collection', 'target']
        title = 'title'
        message = {'action': 'add_link', 'ressource_id': self.ressource_id,
                   'relation': relation, 'target_id': target_id,
                   'title': title}
        self.assertEqual(self.collection.on_message(**message),
                         "OK")

        # Check that document is updated
        expected_data = self.ressource_data.copy()
        expected_data.update({'_links':
                             {relation: [{"target_id": target_id,
                                          "title": title}],
                              'latest': {target_id[0]: target_id}}})
        expected_document = {'ressource_id': self.ressource_id,
                             'ressource_data': expected_data}


        message = {'action': 'get', 'ressource_id': self.ressource_id}
        self.assertEqual(self.collection.on_message(**message),
                         expected_document)

        # Check event payload
        expected_payload = self.event_payload.copy()
        expected_payload.update({'action': 'add_link', 'target_id': target_id,
                                 'title': title, 'relation': relation})

        event_topic = '%s.add_link.%s' % (self.ressource_name, self.ressource_id)
        self.service.publish.assert_called_once_with(event_topic,
                                                     expected_payload)

        # Add another link on same relation
        relation = 'relation_type'
        target_id2 = ['collection', 'target2']
        title2 = 'title2'
        message = {'action': 'add_link', 'ressource_id': self.ressource_id,
                   'relation': relation, 'target_id': target_id2,
                   'title': title2}
        self.assertEqual(self.collection.on_message(**message),
                         "OK")

        # Check that document is updated
        expected_data = self.ressource_data.copy()
        expected_data.update({'_links':
                             {relation: [{"target_id": target_id,
                                          "title": title},
                                         {"target_id": target_id2,
                                          "title": title2}],
                              'latest': {target_id2[0]: target_id2}}})
        expected_document = {'ressource_id': self.ressource_id,
                             'ressource_data': expected_data}

        message = {'action': 'get', 'ressource_id': self.ressource_id}
        self.assertEqual(self.collection.on_message(**message),
                         expected_document)

        # Add a third link on another relation
        relation2 = 'relation_type2'
        target_id3 = ['foo', 'bar']
        title3 = 'title3'
        message = {'action': 'add_link', 'ressource_id': self.ressource_id,
                   'relation': relation2, 'target_id': target_id3,
                   'title': title3}
        self.assertEqual(self.collection.on_message(**message),
                         "OK")

        # Check that document is updated
        expected_data = self.ressource_data.copy()
        expected_data.update({'_links':
                             {relation: [{"target_id": target_id,
                                          "title": title},
                                         {"target_id": target_id2,
                                          "title": title2}],
                              relation2: [{"target_id": target_id3,
                                           "title": title3}],
                              'latest': {target_id2[0]: target_id2,
                                         target_id3[0]: target_id3}}})
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
        expected = [{'ressource_id': x[1], 'ressource_data': x[0]} for x in
                    docs]
        self.assertItemsEqual(self.collection.on_message(**message),
                              expected)

        # Field1 = 1
        message = {'action': 'list', 'where': {'field1': 1}}
        expected = [{'ressource_id': x[1], 'ressource_data': x[0]} for x in
                    docs if x[0]['field1'] == 1]
        self.assertItemsEqual(self.collection.on_message(**message),
                              expected)

        # Field1 = 3
        message = {'action': 'list', 'where': {'field1': 3}}
        expected = [{'ressource_id': x[1], 'ressource_data': x[0]} for x in
                    docs if x[0]['field1'] == 3]
        self.assertItemsEqual(self.collection.on_message(**message),
                              expected)

        # Field2 = 2
        message = {'action': 'list', 'where': {'field2': 2}}
        expected = [{'ressource_id': x[1], 'ressource_data': x[0]} for x in
                    docs if x[0]['field2'] == 2]
        self.assertItemsEqual(self.collection.on_message(**message),
                              expected)
