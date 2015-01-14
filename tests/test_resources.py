import sys
import unittest

from zeroservices import ResourceService, ResourceCollection, ResourceWorker
from zeroservices.resources import NoActionHandler, is_callable, Resource
from zeroservices.exceptions import UnknownService, ResourceException
from .utils import test_medium, sample_collection, sample_resource, base_resource, TestCase
from copy import deepcopy


try:
    from unittest.mock import call, Mock, patch, sentinel
except ImportError:
    from mock import call, Mock, patch, sentinel


class ResourceServiceTestCase(TestCase):

    def setUp(self):
        self.name = "TestService"
        self.medium = test_medium()
        self.service = ResourceService(self.name, self.medium)

    def test_service_info(self):
        service_info = self.service.service_info()
        self.assertEqual(service_info['name'], self.name)
        self.assertEqual(list(service_info['resources']), [])
        self.assertEqual(service_info['node_type'], 'node')

    def test_on_join(self):
        resource = 'TestResource'

        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service',
                     'resources': [resource], 'node_type': 'node'}

        self.service.on_registration_message(node_info)
        self.assertEqual(self.service.nodes_directory,
                         {node_info['node_id']: node_info})
        self.assertEqual(self.service.resources_directory,
                         {resource: node_info['node_id']})

        self.assertEqual(self.medium.send_registration_answer.call_count, 1)
        mock_call = self.medium.send_registration_answer.call_args
        self.assertEqual(mock_call, call(node_info))

        self.assertEqual(self.medium.connect_to_node.call_count, 1)
        mock_call = self.medium.connect_to_node.call_args
        self.assertEqual(mock_call, call(node_info))

        self.assertEqual(self.service.on_peer_join.call_count, 1)
        mock_call = self.service.on_peer_join.call_args
        self.assertEqual(mock_call, call(node_info))

    @unittest.skipIf(sys.version_info[0] > 2,
                     "Check if unicode is supported on python 2")
    def test_join_unicode(self):
        resource = u'TestResource'

        self.service.on_peer_join = Mock()
        node_info = {u'node_id': u'sample', u'name': u'Sample Service',
                     u'resources': [resource], u'node_type': u'node'}

        self.service.on_registration_message(node_info)
        self.assertEqual(self.service.nodes_directory,
                         {node_info['node_id']: node_info})
        self.assertEqual(self.service.resources_directory,
                         {resource: node_info['node_id']})

    def test_resource_registration(self):
        resource_name = 'TestCollection'
        collection = sample_collection(resource_name)

        self.service.register_resource(collection)
        service_info = self.service.service_info()
        self.assertEqual(service_info['name'], self.name)
        self.assertEqual(list(service_info['resources']), [resource_name])

    def test_resource_send(self):
        resource = 'TestResource'
        action = 'list'
        args = {'key': 'value', 'key2': 'value2'}
        resource_id = 'UUID1'

        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service',
                     'resources': [resource], 'node_type': 'node'}

        self.service.on_registration_message(node_info)

        call_request = {'collection': resource, 'action': action,
            'args': args, 'resource_id': resource_id}

        medium_mock_send = self.medium.send
        response = {'response': 'Foo'}
        medium_mock_send.return_value = {'success': True, 'data': response}

        result = self.service.send(**call_request)

        # Test that ResourceService.send return only data, not envelope
        self.assertEqual(result, response)

        # Check call
        self.assertEqual(medium_mock_send.call_count, 1)
        mock_call = medium_mock_send.call_args
        self.assertEqual(mock_call, call(node_info, call_request))

    def test_resource_send_exception(self):
        resource = 'TestResource'
        action = 'list'
        args = {'key': 'value', 'key2': 'value2'}
        resource_id = 'UUID1'

        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service',
                     'node_type': 'node', 'resources': [resource]}

        self.service.on_registration_message(node_info)

        call_request = {'collection': resource, 'action': action,
            'args': args, 'resource_id': resource_id}

        medium_mock_send = self.medium.send
        response = 'Error message'
        medium_mock_send.return_value = {'success': False, 'data': response}

        with self.assertRaises(ResourceException) as cm:
            self.service.send(**call_request)

        # Check exception
        self.assertEquals(cm.exception.error_message, response)

        # Check call
        self.assertEqual(medium_mock_send.call_count, 1)
        mock_call = medium_mock_send.call_args
        self.assertEqual(mock_call, call(node_info, call_request))

    def test_resource_send_unknown_service(self):
        resource = 'TestResource'
        action = 'list'
        args = {'key': 'value', 'key2': 'value2'}
        resource_id = 'UUID1'

        call_request = {'collection': resource, 'action': action,
            'args': args, 'resource_id': resource_id}

        with self.assertRaises(UnknownService):
            self.service.send(**call_request)

    def test_resource_publish_to_itself(self):
        resource_name = 'ABC'

        publish_message = {'type': 'new', '_id': 'foo',
             'resource_data': 'bar', 'resource_name': resource_name}
        topic = '{}.{}'.format(resource_name, 'action')

        with patch.object(self.service, 'on_event') as mocked_on_event:
            self.service.publish(topic, publish_message)

        self.assertEquals(mocked_on_event.call_args_list,
                          [call(topic, publish_message)])


class ResourceServiceFakeCollectionTestCase(TestCase):

    def setUp(self):
        self.name = "TestService"
        self.medium = test_medium()
        self.service = ResourceService(self.name, self.medium)

        self.resource_name = 'TestCollection'
        self.collection = sample_collection(self.resource_name)
        self.service.register_resource(self.collection)

    def test_resource_query(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2, 'action': 'Foo'}
        message = {'collection': self.resource_name}
        message.update(message_args)

        response = {'response': 'Foo'}
        self.collection.on_message.return_value = response

        self.assertEqual(self.service.on_message(**message),
                         {'success': True, 'data': response})

        self.assertEqual(self.collection.on_message.call_count, 1)
        self.assertEqual(self.collection.on_message.call_args, call(**message_args))

    def test_resource_query_no_matching_collection(self):
        resource_name = 'OtherResource'

        message_args = {'kwarg_1': 1, 'kwarg_2': 2}
        message = {'collection': resource_name}
        message.update(message_args)

        self.assertNotEquals(resource_name, self.resource_name)

        response = {'response': 'Foo'}
        self.collection.on_message.return_value = response

        result = self.service.on_message(**message)

        self.assertEqual(self.collection.on_message.call_count, 0)

        self.assertEqual(result['success'], False)
        self.assertTrue(resource_name in result['message'])

    def test_resource_query_exception(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2, 'action': 'Bar'}
        message = {'collection': self.resource_name}
        message.update(message_args)

        error_message = 'OUPS'
        self.collection.on_message.side_effect = Exception(error_message)

        self.assertEqual(self.service.on_message(**message),
                         {'success': False, 'data': error_message})

        self.assertEqual(self.collection.on_message.call_count, 1)

    def test_resource_send_local_collection(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2, 'action': 'Foo'}
        message = {'collection': self.resource_name}
        message.update(message_args)

        response = {'response': 'Foo'}
        self.collection.on_message.return_value = response

        self.assertEqual(self.service.send(**message),
                         response)

        self.assertEqual(self.collection.on_message.call_count, 1)
        default_message_type = "message"
        self.assertEqual(self.collection.on_message.call_args,
            call(**message_args))


class ResourceCollectionTestCase(TestCase):

    def setUp(self):
        self.resource_name = 'Test'

        self.service = sentinel.service

        self.resource_class, self.resource_instance = sample_resource()

        self.collection = ResourceCollection(self.resource_class, 'resource')
        self.collection.resource_name = self.resource_name
        self.collection.service = self.service


    def test_process_message(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2}
        query = {'action': 'list'}
        query.update(message_args)

        with patch.object(self.collection, 'list') as mock:
            return_value = [42]
            mock.return_value = return_value

            self.assertEqual(self.collection.on_message(**query),
                             return_value)

        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args, call(**message_args))

    def test_process_message_bad_action(self):
        return_value = 42

        class CustomCollection(ResourceCollection):

            @is_callable
            def test(self):
                return return_value

        action_name = "test"
        query = {'action': action_name}

        collection = CustomCollection(self.resource_class, 'resource')
        self.assertEqual(collection.on_message(**query), return_value)

    def test_process_message_custom_action(self):
        class CustomCollection(ResourceCollection):

            def test(self):
                pass

        action_name = "test"
        query = {'action': action_name}

        collection = CustomCollection(self.resource_class, 'resource')

        with self.assertRaises(NoActionHandler):
            collection.on_message(**query)

    def test_process_message_no_handler(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2}
        query = {'action': 'unknown'}
        query.update(message_args)

        with self.assertRaises(NoActionHandler):
            self.collection.on_message(**query)

    def test_process_message_create(self):
        resource_id = 'UUID1'
        message_args = {'resource_data': {'kwarg_1': 1, 'kwarg_2': 2},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.resource_instance.create.return_value = sentinel.resource

        self.assertEqual(self.collection.on_message(**query),
                         sentinel.resource)

        self.resource_class.assert_called_once_with(
            resource_collection=self.collection,
            resource_id=resource_id, service=self.service)

        del message_args['resource_id']
        self.resource_instance.create.assert_called_once_with(**message_args)

    def test_process_message_patch(self):
        resource_id = 'UUID1'
        message_args = {'patch': {'kwarg_1': 1, 'kwarg_2': 2},
                        'resource_id': resource_id}
        query = {'action': 'patch'}
        query.update(message_args)

        self.resource_instance.patch.return_value = sentinel.resource

        self.assertEqual(self.collection.on_message(**query),
                         sentinel.resource)

        self.resource_class.assert_called_once_with(
            resource_collection=self.collection,
            resource_id=resource_id, service=self.service)

        del message_args['resource_id']
        self.resource_instance.patch.assert_called_once_with(**message_args)


    def test_process_message_delete(self):
        resource_id = 'UUID1'
        message_args = {'resource_id': resource_id}
        query = {'action': 'delete'}
        query.update(message_args)

        self.resource_instance.delete.return_value = sentinel.resource

        self.assertEqual(self.collection.on_message(**query), sentinel.resource)

        self.resource_class.assert_called_once_with(
            resource_collection=self.collection,
            resource_id=resource_id, service=self.service)

        del message_args['resource_id']
        self.resource_instance.delete.assert_called_once_with()

    def test_publish(self):
        event_topic = 'topic'
        publish_message = {'type': 'new', '_id': 'foo',
             'resource_data': 'bar'}

        publish_mock = Mock()
        self.service.publish = publish_mock

        # Publish
        self.collection.publish(event_topic, publish_message)

        # Check that collection added resource_name to message
        publish_message = deepcopy(publish_message)
        publish_message.update({'resource_name': self.resource_name})

        self.assertEqual(publish_mock.call_args_list,
            [call('%s.%s' % (self.resource_name, event_topic),
                  publish_message)])


class ResourceWorkerTestCase(TestCase):

    def setUp(self):
        self.name = "TestService"
        self.medium = test_medium()
        self.resource_name = 'resource'

        self.service = ResourceService(self.name, self.medium)
        collection = sample_collection(self.resource_name)
        self.service.register_resource(collection)

        self.worker_base_name = "sample_worker"

    def test_worker_info(self):

        worker = ResourceWorker(self.worker_base_name, self.medium)

        service_info = worker.service_info()
        self.assertEqual(service_info['node_type'], 'worker')
        self.assertItemsEqual(service_info['resources'], [])

        self.assertEqual(self.medium.register.call_count, 0)

    def test_worker_registration(self):

        resource_name = self.resource_name

        class WorkerSample(ResourceWorker):

            def __init__(self, *args, **kwargs):
                super(WorkerSample, self).__init__(*args, **kwargs)
                self.register(self.sample_action, resource_name)

            def sample_action(self, resource):
                pass

        worker = WorkerSample(self.worker_base_name, self.medium)

        service_info = worker.service_info()
        self.assertEqual(service_info['node_type'], 'worker')
        self.assertItemsEqual(service_info['resources'],
                              [self.resource_name])

        self.assertEqual(self.medium.subscribe.call_count, 1)
        self.assertEqual(self.medium.subscribe.call_args,
                         call(self.resource_name))

    def test_worker_registration_matcher(self):

        resource_name = self.resource_name
        matcher = {'key': 'value'}

        class WorkerSample(ResourceWorker):

            def __init__(self, *args, **kwargs):
                super(WorkerSample, self).__init__(*args, **kwargs)
                self.register(self.sample_action, resource_name, **matcher)

            def sample_action(self, resource):
                pass

        worker = WorkerSample(self.worker_base_name, self.medium)

        service_info = worker.service_info()
        self.assertEqual(service_info['node_type'], 'worker')
        self.assertItemsEqual(service_info['resources'],
                              [self.resource_name])

        self.assertEqual(self.medium.subscribe.call_count, 1)
        self.assertEqual(self.medium.subscribe.call_args,
                         call(self.resource_name))


class ResourceTestCase(TestCase):

    def setUp(self):
        self.resource_name = 'Test'
        self.resource_id = 'Test#1'

        self.service = sentinel.service

        self.collection = ResourceCollection(base_resource(), 'resource')
        self.collection.resource_name = self.resource_name
        self.collection.service = self.service

    def test_publish(self):
        event_topic = 'topic'
        publish_message = {'type': 'new', 'resource_data': 'bar'}

        publish_mock = Mock()
        self.service.publish = publish_mock

        instance = self.collection.instantiate(resource_id=self.resource_id)

        instance.publish(event_topic, publish_message)

        # Check that collection added resource_name to message
        # And that resource added resource_id to message
        publish_message = deepcopy(publish_message)
        publish_message.update({'resource_name': self.resource_name,
            'resource_id': self.resource_id})

        expected_topic = '%s.%s.%s' % (self.resource_name, event_topic,
                                       self.resource_id)
        self.assertEqual(publish_mock.call_args_list,
            [call(expected_topic, publish_message)])

