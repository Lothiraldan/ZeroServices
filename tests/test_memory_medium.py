try:
    from unittest.mock import call
except ImportError:
    from mock import call

from zeroservices.memory import MemoryMedium
from .utils import TestService, TestCase


class MemoryMediumCommunicationTestCase(TestCase):

    def setUp(self):
        self.medium1 = MemoryMedium('node1')
        self.service1 = TestService('service1', self.medium1)
        self.medium1.set_service(self.service1)

        self.medium2 = MemoryMedium('node2')
        self.service2 = TestService('service2', self.medium2)
        self.medium2.set_service(self.service2)

        self.medium3 = MemoryMedium('node3')
        self.service3 = TestService('service3', self.medium3)
        self.medium3.set_service(self.service3)

    def tearDown(self):
        self.service1.close()
        self.service2.close()
        self.service3.close()

    def test_registration(self):
        self.service1.main()
        self.service2.main()
        self.service3.main()

        self.assertItemsEqual(self.service1.get_known_nodes(),
                              ['node2', 'node3'])
        self.assertItemsEqual(self.service2.get_known_nodes(),
                              ['node1', 'node3'])
        self.assertItemsEqual(self.service3.get_known_nodes(),
                              ['node1', 'node2'])

    def test_diffusion(self):
        self.service1.main()
        self.service2.main()
        self.service3.main()

        self.medium1.publish('type1', 'message1')

        self.assertEqual(self.service2.on_event.call_args_list,
                         [call('type1', 'message1')])
        self.assertEqual(self.service3.on_event.call_args_list,
                         [call('type1', 'message1')])

    def test_direct_call(self):
        self.service1.main()
        self.service2.main()
        self.service3.main()

        msg = {'my': 'message'}
        message_type = 'custom'
        result = 'result'

        self.service2.on_message.return_value = result

        self.assertEqual(self.service1.send('node2', msg,
                                            message_type=message_type), result)

        self.assertEqual(self.service2.on_message.call_args_list,
                         [call(message_type=message_type, **msg)])
