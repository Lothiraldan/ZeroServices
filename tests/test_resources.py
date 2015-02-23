import sys
import asyncio
import unittest

from zeroservices import ResourceService, ResourceCollection, ResourceWorker
from zeroservices.resources import NoActionHandler, is_callable, Resource
from zeroservices.exceptions import UnknownService, ResourceException
from zeroservices.discovery.memory import MemoryDiscoveryMedium
from .utils import test_medium, sample_collection, TestCase, _create_test_resource_service, _async_test
from copy import deepcopy


try:
    from unittest.mock import call, Mock, patch, sentinel
except ImportError:
    from mock import call, Mock, patch, sentinel


class ResourceServiceTestCase(TestCase):

    def setUp(self):
        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

        self.name1 = "TestService1"
        self.service1 = _create_test_resource_service(self.name1, loop=self.loop)
        self.node_id1 = self.service1.medium.node_id

        self.name2 = "TestService2"
        self.service2 = _create_test_resource_service(self.name2, loop=self.loop)
        self.node_id2 = self.service2.medium.node_id

        # Create a resource
        self.resource = 'TestResource'
        self.resource_data = {'key': 'value', 'key2': 'value2'}
        self.resource_id = 'UUID1'

        self.collection = sample_collection(self.resource)

        self.service1.register_resource(self.collection)

        message = {'action': 'create', 'resource_id': self.resource_id,
                   'resource_data': self.resource_data}

        self.loop.run_until_complete(self.collection.on_message(**message))

    def tearDown(self):
        self.service1.close()
        self.service2.close()
        self.loop.stop()
        self.loop.close()
        self.service1.medium.check_leak()
        self.service2.medium.check_leak()

    def test_service_info(self):
        service = _create_test_resource_service("test_service_info", loop=self.loop)
        service_info = service.service_info()
        self.assertEqual(service_info['name'], "test_service_info")
        self.assertEqual(list(service_info['resources']), [])
        self.assertEqual(service_info['node_type'], 'node')

    def test_resource_registration(self):
        service_info = self.service1.service_info()
        self.assertEqual(service_info['name'], self.name1)
        self.assertEqual(list(service_info['resources']), [self.resource])

    @_async_test
    def test_resource_send(self):
        action = 'list'

        yield from self.service1.start()
        yield from self.service2.start()

        call_request = {'collection_name': self.resource, 'action': action}
        result = yield from self.service2.send(**call_request)

        self.assertEqual(result, [{'resource_data': self.resource_data,
                                   'resource_id': self.resource_id}])

    @_async_test
    def test_resource_send_exception(self):
        action = 'list'

        yield from self.service1.start()
        yield from self.service2.start()

        call_request = {'collection_name': self.resource, 'action': action,
                        'resource_id': self.resource_id}

        with self.assertRaises(ResourceException) as cm:
            yield from self.service2.send(**call_request)

        self.assertEquals(cm.exception.error_message, "No handler for action list")

    @_async_test
    def test_resource_send_unknown_service(self):
        yield from self.service1.start()
        yield from self.service2.start()

        call_request = {'collection_name': "NotFound", 'action': 'list'}

        with self.assertRaises(UnknownService):
            yield from self.service2.send(**call_request)

    @_async_test
    def test_resource_send_to_itself(self):
        yield from self.service1.start()
        yield from self.service2.start()

        call_request = {'collection_name': self.resource, 'action': 'list'}
        result = yield from self.service1.send(**call_request)

        self.assertEqual(
            result,
            [{'resource_data': self.resource_data,
              'resource_id': self.resource_id}])

    @_async_test
    def test_resource_publish_to_itself(self):
        self.service1.on_event_mock.reset_mock()

        publish_message = {'type': 'new', '_id': 'foo',
                           'resource_data': 'bar', 'resource_name': self.resource}
        topic = '{}.{}'.format(self.resource, 'action')

        yield from self.service1.publish(topic, publish_message)

        self.assertEquals(self.service1.on_event_mock.call_args_list,
                          [call(topic, publish_message)])

# class ResourceWorkerTestCase(TestCase):

#     def setUp(self):
#         self.name = "TestService"
#         self.medium = test_medium()
#         self.resource_name = 'resource'

#         self.service = ResourceService(self.name, self.medium)
#         collection = sample_collection(self.resource_name)
#         self.service.register_resource(collection)

#         self.worker_base_name = "sample_worker"

#     def test_worker_info(self):

#         worker = ResourceWorker(self.worker_base_name, self.medium)

#         service_info = worker.service_info()
#         self.assertEqual(service_info['node_type'], 'worker')
#         self.assertItemsEqual(service_info['resources'], [])

#         self.assertEqual(self.medium.register.call_count, 0)

#     def test_worker_registration(self):

#         resource_name = self.resource_name

#         class WorkerSample(ResourceWorker):

#             def __init__(self, *args, **kwargs):
#                 super(WorkerSample, self).__init__(*args, **kwargs)
#                 self.register(self.sample_action, resource_name)

#             def sample_action(self, resource):
#                 pass

#         worker = WorkerSample(self.worker_base_name, self.medium)

#         service_info = worker.service_info()
#         self.assertEqual(service_info['node_type'], 'worker')
#         self.assertItemsEqual(service_info['resources'],
#                               [self.resource_name])

#         self.assertEqual(self.medium.subscribe.call_count, 1)
#         self.assertEqual(self.medium.subscribe.call_args,
#                          call(self.resource_name))

#     def test_worker_registration_matcher(self):

#         resource_name = self.resource_name
#         matcher = {'key': 'value'}

#         class WorkerSample(ResourceWorker):

#             def __init__(self, *args, **kwargs):
#                 super(WorkerSample, self).__init__(*args, **kwargs)
#                 self.register(self.sample_action, resource_name, **matcher)

#             def sample_action(self, resource):
#                 pass

#         worker = WorkerSample(self.worker_base_name, self.medium)

#         service_info = worker.service_info()
#         self.assertEqual(service_info['node_type'], 'worker')
#         self.assertItemsEqual(service_info['resources'],
#                               [self.resource_name])

#         self.assertEqual(self.medium.subscribe.call_count, 1)
#         self.assertEqual(self.medium.subscribe.call_args,
#                          call(self.resource_name))

