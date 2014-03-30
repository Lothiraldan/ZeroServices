import unittest

try:
    from unittest.mock import Mock, call
except ImportError:
    from mock import Mock, call


from .utils import MemoryMedium

class MemoryMediumCommunicationTestCase(unittest.TestCase):

    def setUp(self):
        self.service1 = {'name': 'Service 1'}
        self.event_callback1 = Mock()
        self.msg_callback1 = Mock()
        self.medium1 = MemoryMedium(self.service1, self.event_callback1,
            self.msg_callback1, True)

        self.service2 = {'name': 'Service 2', 'ressources': ['ressource2']}
        self.event_callback2 = Mock()
        self.msg_callback2 = Mock()
        self.medium2 = MemoryMedium(self.service2, self.event_callback2,
            self.msg_callback2, True)

        self.service3 = {'name': 'Service 3'}
        self.event_callback3 = Mock()
        self.msg_callback3 = Mock()
        self.medium3 = MemoryMedium(self.service3, self.event_callback3,
            self.msg_callback3, True)

    def tearDown(self):
        self.medium1.close()
        self.medium2.close()

    def test_diffusion(self):
        self.medium1.publish('type1', 'message1')

        self.assertEqual(self.event_callback2.call_args_list,
            [call('type1', 'message1')])
        self.assertEqual(self.event_callback3.call_args_list,
            [call('type1', 'message1')])

    def test_direct_call(self):
        msg = 'message'
        result = 'result'

        self.msg_callback2.return_value = result

        self.assertEqual(self.medium1.call('ressource2.sample', msg=msg),
            result)
        self.assertEqual(self.msg_callback2.call_args_list, [call('sample', msg=msg)])
