import zmq
import json
import time
import socket
import asyncio

from datetime import timedelta
from time import sleep, time
from copy import copy

try:
    from unittest.mock import Mock, call
except ImportError:
    from mock import Mock, call

from zeroservices.medium.zeromq import ZeroMQMedium
from zeroservices.discovery import MemoryDiscoveryMedium
from .utils import generate_zeromq_medium
from ..utils import TestCase, _async_test


class _BaseMediumTestCase(TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

        self.medium_1 = self.loop.run_until_complete(self.get_medium(self.loop))
        self.medium_2 = self.loop.run_until_complete(self.get_medium(self.loop))

    def tearDown(self):
        self.medium_1.close()
        self.medium_2.close()
        self.loop.stop()
        self.loop.close()
        self.medium_1.check_leak()
        self.medium_2.check_leak()

    @_async_test
    def test_register(self):
        yield from asyncio.sleep(0.1, loop=self.loop)

        expected_medium_2 = copy(self.medium_2.get_node_info())
        expected_medium_2['address'] = '127.0.0.1'
        del expected_medium_2['service_info']

        self.assertEquals(self.medium_1.get_directory(),
                          {self.medium_2.node_id: expected_medium_2})

        expected_medium_1 = copy(self.medium_1.get_node_info())
        expected_medium_1['address'] = '127.0.0.1'
        del expected_medium_1['service_info']

        self.assertEquals(self.medium_2.get_directory(),
                          {self.medium_1.node_id: expected_medium_1})

    @_async_test
    def test_send_no_response(self):
        yield from asyncio.sleep(0.1, loop=self.loop)

        message_type = 'MYMESSAGETYPE'
        message = {'foo': 'bar'}
        on_message = self.medium_2.service.on_message_mock

        on_message.return_value = None

        result = yield from self.medium_1.send(self.medium_2.node_id,
                                               message,
                                               message_type=message_type,
                                               wait_response=False)
        yield from asyncio.sleep(0.1, loop=self.loop)

        self.assertEqual(result, None)

        self.assertEqual(on_message.call_count, 1)
        on_message.assert_called_with(message_type=message_type, **message)

    @_async_test
    def test_send_response(self):
        yield from asyncio.sleep(0.1, loop=self.loop)

        return_value = {'data': 'ReturnValue'}
        message_type = 'MYMESSAGETYPE'
        message = {'foo': 'bar'}
        self.medium_2.service.on_message_mock.return_value = return_value

        result = yield from self.medium_1.send(self.medium_2.node_id,
                                               message,
                                               message_type=message_type)

        self.assertEqual(result, return_value)

    @_async_test
    def test_pub_sub(self):
        yield from asyncio.sleep(0.1, loop=self.loop)

        event_data = {'data': 'foo'}
        event_type = 'EVENT_TYPE'

        yield from self.medium_1.publish(event_type, event_data)
        yield from asyncio.sleep(0.1, loop=self.loop)

        on_event = self.medium_2.service.on_event_mock
        self.assertEqual(on_event.call_count, 1)
        on_event.assert_called_with(event_type, **event_data)

    @_async_test
    def test_pub_sub_custom_event_listener(self):
        yield from asyncio.sleep(0.1, loop=self.loop)

        mock = Mock()

        @asyncio.coroutine
        def custom_event_listener(*args, **kwargs):
            return mock(*args, **kwargs)

        self.medium_2.add_event_listener(custom_event_listener)

        event_data = {'data': 'foo'}
        event_type = 'EVENT_TYPE'

        yield from self.medium_1.publish(event_type, event_data)
        yield from asyncio.sleep(0.1, loop=self.loop)

        self.assertEqual(mock.call_count, 1)
        mock.assert_called_with(event_type, event_data)

    @_async_test
    def test_periodic_call(self):
        periodic_mock = Mock()

        @asyncio.coroutine
        def periodic_called(*args, **kwargs):
            return periodic_mock(*args, **kwargs)

        self.medium_1.periodic_call(periodic_called, 0.1)

        yield from asyncio.sleep(0.15, loop=self.loop)

        self.assertEqual(periodic_mock.call_count, 1)

        yield from asyncio.sleep(0.14, loop=self.loop)

        self.assertEqual(periodic_mock.call_count, 2)
