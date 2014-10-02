from zeroservices import BaseService
from zeroservices.exceptions import UnknownNode
from .utils import test_medium, TestCase

try:
    from unittest.mock import Mock, call
except ImportError:
    from mock import Mock, call


class BaseServiceTestCase(TestCase):

    def setUp(self):
        self.name = "TestService"
        self.medium = test_medium()
        self.service = BaseService(self.name, self.medium)
        self.node_info = {'node_id': 'sample', 'name': 'Sample Service',
                          'node_type': 'node'}

    def test_instantiation(self):
        """Test that service pass itself to the medium
        """
        self.assertEqual(self.medium.set_service.call_count, 1)
        self.assertEqual(self.medium.set_service.call_args,
                         call(self.service))

    def test_service_info(self):
        self.assertEqual(self.service.service_info(),
            {'name': self.name, 'node_type': 'node'})

    def test_on_join(self):
        self.service.on_peer_join = Mock()

        self.service.on_registration_message(self.node_info)
        self.assertEqual(self.service.nodes_directory,
                         {self.node_info['node_id']: self.node_info})

        self.assertEqual(self.medium.send_registration_answer.call_count, 1)
        mock_call = self.medium.send_registration_answer.call_args
        self.assertEqual(mock_call, call(self.node_info))

        self.assertEqual(self.medium.connect_to_node.call_count, 1)
        mock_call = self.medium.connect_to_node.call_args
        self.assertEqual(mock_call, call(self.node_info))

        self.assertEqual(self.service.on_peer_join.call_count, 1)
        mock_call = self.service.on_peer_join.call_args
        self.assertEqual(mock_call, call(self.node_info))

    def test_join_twice(self):
        self.service.on_peer_join = Mock()

        self.service.on_registration_message(self.node_info)
        self.assertEqual(self.service.nodes_directory,
                         {self.node_info['node_id']: self.node_info})
        self.medium.send_registration_answer.reset_mock()
        self.service.on_peer_join.reset_mock()

        self.service.on_registration_message(self.node_info)
        self.assertEqual(self.service.nodes_directory,
                         {self.node_info['node_id']: self.node_info})

        self.assertEqual(self.medium.send_registration_answer.call_count, 0)
        self.assertEqual(self.service.on_peer_join.call_count, 0)

    def test_send(self):
        # Set response on zeromq mock
        response = {'result': True}
        self.medium.send.return_value = response

        self.service.on_registration_message(self.node_info)
        message = {'content': 'Coucou'}
        self.assertEquals(self.service.send(self.node_info['node_id'], message),
                          response)

        self.assertEqual(self.medium.send.call_count, 1)
        mock_call = self.medium.send.call_args
        self.assertEqual(mock_call, call(self.node_info, message))

    def test_send_unknown_node(self):
        message = {'content': 'Coucou'}
        with self.assertRaises(UnknownNode):
            self.service.send('commit', message)
