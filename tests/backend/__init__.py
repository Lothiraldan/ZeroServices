import asyncio

from asyncio import coroutine
from zeroservices import BaseService
from zeroservices.resources import NoActionHandler
from ..utils import test_medium, TestCase, _async_test, _create_test_resource_service

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class _BaseCollectionTestCase(TestCase):

    def setUp(self):
        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

        self.service = _create_test_resource_service('test_service', self.loop)
        self.loop.run_until_complete(self.service.start())
        self.service2 = _create_test_resource_service('test_listener', self.loop)
        self.loop.run_until_complete(self.service2.start())

        # Resource
        self.resource_id = 'UUID-1'
        self.resource_data = {'field1': 1, 'field2': 2}
        self.resource_name = 'test_collection'

        self.event_payload = {'resource_id': self.resource_id,
                              'resource_name': self.resource_name}

        self.maxDiff = None

    def tearDown(self):
        self.service.close()
        self.service2.close()
        self.loop.stop()
        self.loop.close()
        self.service.medium.check_leak()
        self.service2.medium.check_leak()

    def _create(self, resource_data, resource_id):
        message = {'action': 'create', 'resource_id': resource_id,
                   'resource_data': resource_data}
        yield from self.collection.on_message(**message)

    @_async_test
    def test_create(self):
        message = {'action': 'create', 'resource_id': self.resource_id,
                   'resource_data': self.resource_data}

        result = yield from self.collection.on_message(**message)
        self.assertEqual(result, {'resource_id': self.resource_id})

        expected_payload = self.event_payload.copy()
        expected_payload.update({'action': 'create',
                                 'resource_data': self.resource_data})

        event_topic = '%s.create.%s' % (self.resource_name, self.resource_id)
        self.service2.on_event_mock.assert_called_once_with(event_topic,
                                                            **expected_payload)

        self.service2.on_event_mock.reset_mock()

    @_async_test
    def test_get(self):
        yield from self.test_create()

        message = {'action': 'get', 'resource_id': self.resource_id}

        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         {'resource_id': self.resource_id,
                          'resource_data': self.resource_data})

    @_async_test
    def test_update(self):
        yield from self.test_create()

        patch = {'field3': 3, 'field4': 4}
        query = {'$set': patch}

        message = {'action': 'patch', 'resource_id': self.resource_id,
                   'patch': query}

        expected_document = self.resource_data.copy()
        expected_document.update(patch)

        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         expected_document)

        message = {'action': 'get', 'resource_id': self.resource_id}

        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         {'resource_id': self.resource_id,
                          'resource_data': expected_document})

        expected_payload = self.event_payload.copy()
        expected_payload.update({'action': 'patch', 'patch': query})

        event_topic = '%s.patch.%s' % (self.resource_name, self.resource_id)
        self.service2.on_event_mock.assert_called_once_with(event_topic,
                                                            **expected_payload)

    @_async_test
    def test_delete(self):
        yield from self.test_create()

        message = {'action': 'delete', 'resource_id': self.resource_id}

        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         'OK')

        message = {'action': 'get', 'resource_id': self.resource_id}

        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         'NOK')

        expected_payload = self.event_payload.copy()
        expected_payload.update({'action': 'delete'})

        event_topic = '%s.delete.%s' % (self.resource_name, self.resource_id)
        self.service2.on_event_mock.assert_called_once_with(event_topic,
                                                            **expected_payload)

    # Add another link on same relation
    @_async_test
    def test_add_link(self):
        yield from self.test_create()

        relation = 'relation_type'
        target_id = ['collection', 'target']
        title = 'title'
        message = {'action': 'add_link', 'resource_id': self.resource_id,
                   'relation': relation, 'target_id': target_id,
                   'title': title}

        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         "OK")

        # Check that document is updated
        expected_data = self.resource_data.copy()
        expected_data.update({'_links':
                             {relation: [{"target_id": target_id,
                                          "title": title}],
                              'latest': {target_id[0]: target_id}}})
        expected_document = {'resource_id': self.resource_id,
                             'resource_data': expected_data}


        message = {'action': 'get', 'resource_id': self.resource_id}
        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         expected_document)

        # Check event payload
        expected_payload = self.event_payload.copy()
        expected_payload.update({'action': 'add_link', 'target_id': target_id,
                                 'title': title, 'relation': relation})

        event_topic = '%s.add_link.%s' % (self.resource_name, self.resource_id)
        self.service2.on_event_mock.assert_called_once_with(event_topic,
                                                            **expected_payload)

        # Add another link on same relation
        relation = 'relation_type'
        target_id2 = ['collection', 'target2']
        title2 = 'title2'
        message = {'action': 'add_link', 'resource_id': self.resource_id,
                   'relation': relation, 'target_id': target_id2,
                   'title': title2}
        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         "OK")

        # Check that document is updated
        expected_data = self.resource_data.copy()
        expected_data.update({'_links':
                             {relation: [{"target_id": target_id,
                                          "title": title},
                                         {"target_id": target_id2,
                                          "title": title2}],
                              'latest': {target_id2[0]: target_id2}}})
        expected_document = {'resource_id': self.resource_id,
                             'resource_data': expected_data}

        message = {'action': 'get', 'resource_id': self.resource_id}
        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         expected_document)

        # Add a third link on another relation
        relation2 = 'relation_type2'
        target_id3 = ['foo', 'bar']
        title3 = 'title3'
        message = {'action': 'add_link', 'resource_id': self.resource_id,
                   'relation': relation2, 'target_id': target_id3,
                   'title': title3}
        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         "OK")

        # Check that document is updated
        expected_data = self.resource_data.copy()
        expected_data.update({'_links':
                             {relation: [{"target_id": target_id,
                                          "title": title},
                                         {"target_id": target_id2,
                                          "title": title2}],
                              relation2: [{"target_id": target_id3,
                                           "title": title3}],
                              'latest': {target_id2[0]: target_id2,
                                         target_id3[0]: target_id3}}})
        expected_document = {'resource_id': self.resource_id,
                             'resource_data': expected_data}

        message = {'action': 'get', 'resource_id': self.resource_id}
        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         expected_document)

    @_async_test
    def test_list(self):
        message = {'action': 'list'}

        # Check that list doesn't return anything
        result = yield from self.collection.on_message(**message)
        self.assertEqual(result, [])

        # Create a doc
        yield from self.test_create()

        # Check that list return the document
        result = yield from self.collection.on_message(**message)
        self.assertEqual(result,
                         [{'resource_id': self.resource_id,
                          'resource_data': self.resource_data}])

    @_async_test
    def test_list_filter(self):
        doc_1 = ({'field1': 1, 'field2': 2}, 'UUID-1')
        doc_2 = ({'field1': 3, 'field2': 2}, 'UUID-2')
        doc_3 = ({'field1': 1, 'field2': 4}, 'UUID-3')
        docs = (doc_1, doc_2, doc_3)

        for doc in docs:
            yield from self._create(*doc)

        # All docs
        message = {'action': 'list'}
        expected = [{'resource_id': x[1], 'resource_data': x[0]} for x in
                    docs]
        result = yield from self.collection.on_message(**message)
        self.assertItemsEqual(result,
                              expected)

        # Field1 = 1
        message = {'action': 'list', 'where': {'field1': 1}}
        expected = [{'resource_id': x[1], 'resource_data': x[0]} for x in
                    docs if x[0]['field1'] == 1]
        result = yield from self.collection.on_message(**message)
        self.assertItemsEqual(result,
                              expected)

        # Field1 = 3
        message = {'action': 'list', 'where': {'field1': 3}}
        expected = [{'resource_id': x[1], 'resource_data': x[0]} for x in
                    docs if x[0]['field1'] == 3]
        result = yield from self.collection.on_message(**message)
        self.assertItemsEqual(result,
                              expected)

        # Field2 = 2
        message = {'action': 'list', 'where': {'field2': 2}}
        expected = [{'resource_id': x[1], 'resource_data': x[0]} for x in
                    docs if x[0]['field2'] == 2]
        result = yield from self.collection.on_message(**message)
        self.assertItemsEqual(result,
                              expected)

    @_async_test
    def test_bad_action(self):
        message = {'action': 'unknown', 'resource_id': self.resource_id,
                   'resource_data': self.resource_data}

        with self.assertRaises(NoActionHandler):
            yield from self.collection.on_message(**message)
