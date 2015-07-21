import asyncio

from copy import copy

from zeroservices import BaseService
from zeroservices.medium.memory import MemoryMedium
from zeroservices.discovery.memory import MemoryDiscoveryMedium
from zeroservices.exceptions import UnknownNode
from .utils import TestCase, _create_test_service, _async_test

try:
    from unittest.mock import Mock, patch, call
except ImportError:
    from mock import Mock, patch, call


class BaseServiceTestCase(TestCase):

    def setUp(self):
        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

        self.name1 = "TestService1"
        self.node_info1 = {'foo': 'bar'}
        self.service1 = _create_test_service(self.name1, self.node_info1, self.loop)
        self.node_id1 = self.service1.medium.node_id

        self.name2 = "TestService2"
        self.node_info2 = {'foo2': 'babar'}
        self.service2 = _create_test_service(self.name2, self.node_info2, self.loop)
        self.node_id2 = self.service2.medium.node_id

    def tearDown(self):
        self.service1.close()
        self.service2.close()
        self.loop.stop()
        self.loop.close()
        self.service1.medium.check_leak()
        self.service2.medium.check_leak()

    def test_service_info(self):
        expected = {'name': self.name1, 'node_type': 'node'}
        expected.update(self.node_info1)
        self.assertEqual(self.service1.service_info(), expected)

        expected = {'name': self.name2, 'node_type': 'node'}
        expected.update(self.node_info2)
        self.assertEqual(self.service2.service_info(), expected)

    @_async_test
    def test_register(self):
        yield from self.service1.start()
        yield from self.service2.start()

        def _expected_infos(service):
            service_info = copy(service.service_info())
            service_info['node_id'] = service.medium.node_id
            return {service.medium.node_id: service_info}

        self.assertEqual(self.service1.get_directory(), _expected_infos(self.service2))
        self.assertEqual(self.service2.get_directory(), _expected_infos(self.service1))

    @_async_test
    def test_send(self):
        yield from self.service1.start()
        yield from self.service2.start()

        response = {'response': 'Pong'}
        self.service2.on_message_mock.return_value = response

        message = {'content': 'Ping'}
        result = yield from self.service1.send(self.node_id2, message)

        self.assertEqual(result, response)
        self.service2.on_message_mock.assert_called_once_with(message_type='message', **message)

    @_async_test
    def test_publish(self):
        yield from self.service1.start()
        yield from self.service2.start()

        event_type = 'EVENT_TYPE'
        event_message = {'foo': 'bar', 'foo2': 'babar'}
        yield from self.service1.publish(event_type, event_message)

        self.service2.on_event_mock.assert_called_once_with(event_type, **event_message)
