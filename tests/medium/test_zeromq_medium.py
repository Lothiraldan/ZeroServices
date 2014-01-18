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
        from zmq.eventloop.ioloop import IOLoop
        self.ioloop = IOLoop.instance()
        self.service1 = generate_zeromq_medium({'name': 'Service 1'}, ioloop=self.ioloop)
        self.service2 = generate_zeromq_medium({'name': 'Service 2'}, ioloop=self.ioloop)

    def tearDown(self):
        self.service1.medium.close()
        self.service2.medium.close()

    def stop_loop(self, *args, **kwargs):
        self.ioloop.stop()

    def test_register(self):
        self.service1.medium.register()

        # Same ioloop for both services
        self.ioloop.start()

        self.assertEqual(self.service2.on_registration_message.call_count, 1)
        service2_registration_message = self.service2.on_registration_message.call_args[0][0]
        self.assertEqual(service2_registration_message['name'], 'Service 1')
        self.assertEqual(service2_registration_message['pub_port'], self.service1.medium.pub_port)
        self.assertEqual(service2_registration_message['server_port'], self.service1.medium.server_port)
        self.assertEqual(service2_registration_message['node_id'], self.service1.medium.node_id)

        self.assertEqual(self.service1.on_registration_message.call_count, 1)
        service1_registration_message = self.service1.on_registration_message.call_args[0][0]
        self.assertEqual(service1_registration_message['name'], 'Service 1')
        self.assertEqual(service1_registration_message['pub_port'], self.service1.medium.pub_port)
        self.assertEqual(service1_registration_message['server_port'], self.service1.medium.server_port)
        self.assertEqual(service1_registration_message['node_id'], self.service1.medium.node_id)

        self.assertEqual(service2_registration_message['address'],
                         service1_registration_message['address'])

    def test_register_custom_node_id(self):
        self.service1.medium.close()

        # Set node id
        service = generate_zeromq_medium({'name': 'custom'}, node_id='custom')
        service.medium.register()

        # Same ioloop for both services
        self.ioloop.start()

        self.assertEqual(self.service2.on_registration_message.call_count, 1)
        service2_registration_message = self.service2.on_registration_message.call_args[0][0]
        self.assertEqual(service2_registration_message['name'], 'custom')
        self.assertEqual(service2_registration_message['pub_port'], service.medium.pub_port)
        self.assertEqual(service2_registration_message['server_port'], service.medium.server_port)
        self.assertEqual(service2_registration_message['node_id'], service.medium.node_id)

    def test_register_answer(self):
        self.service1.medium.register()

        # Same ioloop for both services
        self.ioloop.start()

        service2_registration_message = self.service2.on_registration_message.call_args[0][0]
        address = service2_registration_message['address']

        # Send answer
        self.service2.medium.send_registration_answer(service2_registration_message)

        self.ioloop.start()

        self.assertEqual(self.service1.on_registration_message.call_count, 2)
        service1_registration_message = self.service1.on_registration_message.call_args[0][0]
        self.assertEqual(service1_registration_message['name'], 'Service 2')
        self.assertEqual(service1_registration_message['pub_port'], self.service2.medium.pub_port)
        self.assertEqual(service1_registration_message['server_port'], self.service2.medium.server_port)
        self.assertEqual(address, service1_registration_message['address'])

    def test_sub_connection_then_publish(self):
        self.service1.medium.register()

        # Same ioloop for both services
        self.ioloop.start()

        service2_registration_message = self.service2.on_registration_message.call_args[0][0]
        self.service2.medium.connect_to_node(service2_registration_message)

        self.service1.medium.publish('Test', 'Test')

        self.ioloop.start()

        self.assertEqual(self.service2.on_event.call_count, 1)
        service2_event_message = self.service2.on_event.call_args
        self.assertEqual(service2_event_message, call('Test', 'Test'))

    def test_direct_message(self):
        self.service1.medium.register()

        self.ioloop.start()

        r_msg = self.service2.on_registration_message.call_args[0][0]

        # Mock sync_get_response
        return_value = {'success': True}
        self.service2.medium._sync_get_response = Mock()
        self.service2.medium._sync_get_response.return_value = return_value

        # Send message with default message_type
        message = {'hello': 'world'}
        self.assertEqual(self.service2.medium.send(r_msg, message),
                         return_value)

        self.ioloop.start()

        self.assertEqual(self.service1.on_message.call_count, 1)
        service1_message = self.service1.on_message.call_args
        self.assertEqual(service1_message, call(**message))

    def test_direct_message_answer(self):
        return_value = {'ping': 'pong'}
        self.service1.on_message.side_effect = None
        self.service1.on_message.return_value = return_value

        self.service1.medium.register()

        self.ioloop.start()

        r_msg = self.service2.on_registration_message.call_args[0][0]

        # Send message with default message_type
        message = {'ping': 'ping'}

        # Create stop callback which stop ioloop
        stop = Mock()
        stop.side_effect = self.stop_loop

        self.service2.medium.send(r_msg, message, callback=stop)
        self.ioloop.start()

        self.assertEqual(stop.call_count, 1)
        response = stop.call_args

        self.assertEqual(response, call(return_value))


class ZeroMQMediumRegistrationTestCase(ZeroMQMediumRegistrationTestCase):

    def tearDown(self):
        self.service2.medium.close()

    def test_close(self):
        # Install ioloop onlt on these services
        # Do not process close message

        self.service1.on_peer_leave.side_effect = self.stop_loop
        self.service2.on_peer_leave.side_effect = self.stop_loop

        self.service1.medium.register()
        self.ioloop.start()

        service2_registration_message = self.service2.on_registration_message.call_args[0][0]
        self.service2.medium.connect_to_node(service2_registration_message)

        self.service2.medium.register()
        self.ioloop.start()

        # Connect both of them
        service1_registration_message = self.service1.on_registration_message.call_args[0][0]
        self.service1.medium.connect_to_node(service1_registration_message)

        self.assertEqual(self.service2.on_registration_message.call_count, 2)
        self.assertEqual(self.service1.on_registration_message.call_count, 2)

        self.service2.on_peer_leave.reset_mock()
        self.service1.medium.close()

        self.ioloop.start()
        self.assertEqual(self.service2.on_peer_leave.call_count, 1)
        service2_close_message = self.service2.on_peer_leave.call_args[0][0]
        self.assertEqual(service2_registration_message['node_id'], self.service1.medium.node_id)

if __name__ == '__main__':
    unittest.main()
