import asyncio
import unittest
from zeroservices import BaseService
from ..utils import test_medium, TestCase, _async_test

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class _BaseDiscoveryMediumTestCase(TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

        self.mock_1 = Mock()
        self.mock_1.__name__ = 'Mock1'
        self.mock_2 = Mock()
        self.mock_2.__name__ = 'Mock2'

        self.node_info_1 = {'node_id': '#ID1', 'service_info': {'name': '#S1'}}
        self.node_info_2 = {'node_id': '#ID2', 'service_info': {'name': '#S2'}}

        self.first_discovery_medium = self.loop.run_until_complete(self.get_medium(self.mock_1, self.loop, self.node_info_1))
        self.second_discovery_medium = self.loop.run_until_complete(self.get_medium(self.mock_2, self.loop, self.node_info_2))

    def tearDown(self):
        self.first_discovery_medium.close()
        self.second_discovery_medium.close()
        self.loop.stop()
        self.loop.close()
        self.first_discovery_medium.check_leak()
        self.second_discovery_medium.check_leak()

    @_async_test
    def test_discovery(self):
        yield from self.first_discovery_medium.send_registration_infos()
        yield from self.second_discovery_medium.send_registration_infos()

        # Wait some time for message propagation
        yield from asyncio.sleep(0.01, loop=self.loop)

        # Check that we received some informations in second medium
        self.assertEqual(self.mock_2.call_count, 1)
        call = self.mock_2.call_args[0]
        self.assertEqual(call[0], 'register')
        self.assertDictIsSubset(self.node_info_1, call[1])
        address_1 = call[1]['address']

        # Check that we receive some informations in first medium
        self.assertEqual(self.mock_1.call_count, 1)
        call = self.mock_1.call_args[0]
        self.assertEqual(call[0], 'register')
        self.assertDictIsSubset(self.node_info_2, call[1])
        address_2 = call[1]['address']

        self.assertEqual(address_1, address_2)

    @_async_test
    def test_node_info_immutability(self):
        # Mutate node info 1 and check that the right message is sent
        self.node_info_1['node_id'] = 'New #ID1'

        yield from self.first_discovery_medium.send_registration_infos()


        # Wait some time for message propagation
        yield from asyncio.sleep(0.01, loop=self.loop)

        # Check that we received some informations in second medium
        self.assertEqual(self.mock_2.call_count, 1)
        call = self.mock_2.call_args[0]
        self.assertEqual(call[0], 'register')
        self.assertDictIsSubset({'node_id': '#ID1'}, call[1])
