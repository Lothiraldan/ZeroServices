import unittest

try:
    from unittest.mock import Mock, call
except ImportError:
    from mock import Mock, call

from zeroservices import BaseService
from .utils import MemoryMedium

class MemoryMediumCommunicationTestCase(unittest.TestCase):

    def setUp(self):
        self.medium1 = MemoryMedium('node1')
        self.service1 = BaseService('service1', self.medium1)
        self.medium1.set_service(self.service1)

        self.medium2 = MemoryMedium('node2')
        self.service2 = BaseService('service2', self.medium2)
        self.medium2.set_service(self.service2)

    def tearDown(self):
        self.service1.close()
        self.service2.close()


    def test_registration(self):
        self.service1.main()
        self.service2.main()

        self.assertEqual(self.service1.nodes_directory.keys(), ['node2'])
        self.assertEqual(self.service2.nodes_directory.keys(), ['node1'])

    # def test_diffusion(self):
    #     self.medium1.publish('type1', 'message1')

    #     self.assertEqual(self.event_callback2.call_args_list,
    #         [call('type1', 'message1')])
    #     self.assertEqual(self.event_callback3.call_args_list,
    #         [call('type1', 'message1')])

    # def test_direct_call(self):
    #     msg = 'message'
    #     result = 'result'

    #     self.msg_callback2.return_value = result

    #     self.assertEqual(self.medium1.call('ressource2.sample', msg=msg),
    #         result)
    #     self.assertEqual(self.msg_callback2.call_args_list, [call('sample', msg=msg)])
