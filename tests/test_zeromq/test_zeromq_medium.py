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
from utils import generate_zeromq_medium


class ZeroMQMediumRegistrationTestCase(unittest.TestCase):

    def setUp(self):
        self.service1 = generate_zeromq_medium({'name': 'Service 1'})
        self.service2 = generate_zeromq_medium({'name': 'Service 2'})

    def tearDown(self):
        self.service1.medium.close()
        self.service2.medium.close()

    def test_register(self):
        self.service1.medium.register()

        # Same ioloop for both services
        self.service2.medium.start()

        self.assertEqual(self.service2.on_registration_message.call_count, 1)
        service2_registration_message = self.service2.on_registration_message.call_args[0][0]
        self.assertEqual(service2_registration_message['name'], 'Service 1')
        self.assertEqual(service2_registration_message['pub_port'], self.service1.medium.pub_port)
        self.assertEqual(service2_registration_message['server_port'], self.service1.medium.server_port)

        self.assertEqual(self.service1.on_registration_message.call_count, 1)
        service1_registration_message = self.service1.on_registration_message.call_args[0][0]
        self.assertEqual(service1_registration_message['name'], 'Service 1')
        self.assertEqual(service1_registration_message['pub_port'], self.service1.medium.pub_port)
        self.assertEqual(service1_registration_message['server_port'], self.service1.medium.server_port)

        self.assertEqual(service2_registration_message['address'],
                         service1_registration_message['address'])

    def test_register_answer(self):
        self.service1.medium.register()

        # Same ioloop for both services
        self.service2.medium.start()

        service2_registration_message = self.service2.on_registration_message.call_args[0][0]
        address = service2_registration_message['address']

        # Send answer
        self.service2.medium.send_registration_answer(service2_registration_message)

        self.service1.medium.start()

        self.assertEqual(self.service1.on_registration_message.call_count, 2)
        service1_registration_message = self.service1.on_registration_message.call_args[0][0]
        self.assertEqual(service1_registration_message['name'], 'Service 2')
        self.assertEqual(service1_registration_message['pub_port'], self.service2.medium.pub_port)
        self.assertEqual(service1_registration_message['server_port'], self.service2.medium.server_port)
        self.assertEqual(address, service1_registration_message['address'])

    def test_sub_connection_then_publish(self):
        self.service1.medium.register()

        # Same ioloop for both services
        self.service2.medium.start()

        service2_registration_message = self.service2.on_registration_message.call_args[0][0]
        self.service2.medium.connect_to_node(service2_registration_message)

        self.service1.medium.publish('Test', 'Test')

        self.service2.medium.start()

        self.assertEqual(self.service2.on_event.call_count, 1)
        service2_event_message = self.service2.on_event.call_args
        self.assertEqual(service2_event_message, call('Test', 'Test'))

    def test_direct_message(self):
        self.service1.medium.register()

        # Same ioloop for both services
        self.service2.medium.start()

        r_msg = self.service2.on_registration_message.call_args[0][0]

        # Send message with default message_type
        message = {'hello': 'world'}
        self.service2.medium.send(r_msg['address'], r_msg['server_port'], message)

        self.service1.medium.start()

        self.assertEqual(self.service1.on_message.call_count, 1)
        service1_message = self.service1.on_message.call_args
        self.assertEqual(service1_message, call('message', **message))

        # Send message with custom message_type
        message = {'hello': 'world'}
        message_type = 'Custom'
        self.service2.medium.send(r_msg['address'], r_msg['server_port'], message, message_type)

        self.service1.medium.start()

        self.assertEqual(self.service1.on_message.call_count, 2)
        service1_message = self.service1.on_message.call_args
        self.assertEqual(service1_message, call(message_type, **message))

    def test_direct_message_answer(self):
        return_value = {'ping': 'pong'}
        self.service1.on_message.side_effect = None
        self.service1.on_message.return_value = return_value

        self.service1.medium.register()

        # Same ioloop for both services
        self.service2.medium.start()

        r_msg = self.service2.on_registration_message.call_args[0][0]

        # Send message with default message_type
        message = {'ping': 'ping'}

        # Create stop callback which stop ioloop
        stop = Mock()
        stop.side_effect = lambda *args, **kwargs: self.service2.medium.stop()

        self.service2.medium.send(r_msg['address'], r_msg['server_port'],
                                  message, callback=stop)
        self.service1.medium.start()

        self.assertEqual(stop.call_count, 1)
        response = stop.call_args

        self.assertEqual(response, call(return_value))

if __name__ == '__main__':
    unittest.main()
