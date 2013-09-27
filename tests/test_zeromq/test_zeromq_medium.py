import zmq
import json
import time
import socket
import unittest
import threading

from datetime import timedelta
from time import sleep
from mock import Mock, call

from zeroservices.medium.zeromq import ZeroMQMedium
from utils import run_poller_for


class ZeroMQMediumRegistrationTestCase(unittest.TestCase):

    def setUp(self):
        self.service1 = {'name': 'Service 1'}
        self.medium1 = ZeroMQMedium(self.service1, None, None, True)

        self.service2 = {'name': 'Service 2'}
        self.medium2 = ZeroMQMedium(self.service2, None, None, True)

    def tearDown(self):
        self.medium1.close()
        self.medium2.close()

    def test_register(self):
        self.medium1.register()

        self.medium2.loop(2000)
        # Our own register packet
        self.medium1.loop(2000)
        self.medium1.loop(2000)

        medium1_addr = self.medium2.services[self.service1['name']].pop('address')
        medium2_me_addr = self.medium2.services[self.service1['name']].pop('me')
        self.assertEqual(self.medium2.services, {self.service1['name']:
            {'pub_port': self.medium1.pub_port,
             'server_port': self.medium1.server_port}})

        medium2_addr = self.medium1.services[self.service2['name']].pop('address')
        medium1_me_addr = self.medium1.services[self.service2['name']].pop('me')
        self.assertEqual(self.medium1.services, {self.service2['name']:
            {'pub_port': self.medium2.pub_port,
             'server_port': self.medium2.server_port}})

        self.assertEqual(medium1_addr, medium2_addr)
        self.assertEqual(medium1_addr, medium1_me_addr)
        self.assertEqual(medium2_addr, medium2_me_addr)

class ZeroMQMediumCommunicationTestCase(unittest.TestCase):

    def setUp(self):
        self.service1 = {'name': 'Service 1'}
        self.event_callback1 = Mock()
        self.msg_callback1 = Mock()
        self.medium1 = ZeroMQMedium(self.service1, self.event_callback1,
            self.msg_callback1, True)

        self.service2 = {'name': 'Service 2', 'ressources': ['ressource2']}
        self.event_callback2 = Mock()
        self.msg_callback2 = Mock()
        self.medium2 = ZeroMQMedium(self.service2, self.event_callback2,
            self.msg_callback2, True)

        self.service3 = {'name': 'Service 3'}
        self.event_callback3 = Mock()
        self.msg_callback3 = Mock()
        self.medium3 = ZeroMQMedium(self.service3, self.event_callback3,
            self.msg_callback3, True)

        self.medium1.register()

        # Process medium 1 registration packet
        self.medium2.loop(2000)
        self.medium3.loop(2000)

        # Our own register packet and medium 2 registration packet
        self.medium1.loop(2000)
        # Medium 3 registration packet
        self.medium1.loop(2000)

    def tearDown(self):
        self.medium1.close()
        self.medium2.close()

    def test_diffusion(self):
        self.medium1.publish('type1', 'message1')

        self.medium2.loop(2000)
        self.medium3.loop(2000)

        self.assertEqual(self.event_callback2.call_args_list,
            [call('type1', 'message1')])
        self.assertEqual(self.event_callback3.call_args_list,
            [call('type1', 'message1')])

    def test_direct_call(self):
        msg = 'message'
        result = 'result'

        self.msg_callback2.return_value = result

        run_poller_for(self.medium2, 2000)

        self.assertEqual(self.medium1.call('ressource2', 'sample', msg=msg),
            result)
        self.assertEqual(self.msg_callback2.call_args_list,
            [call(msg='message', collection='ressource2')])

if __name__ == '__main__':
    unittest.main()
