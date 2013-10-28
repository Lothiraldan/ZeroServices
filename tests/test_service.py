import unittest

from zeroservices import BaseService
from utils import TestMedium
from mock import call, Mock


class BaseServiceTestCase(unittest.TestCase):

    def setUp(self):
        self.medium = TestMedium()
        self.service = BaseService(self.medium)

    def test_on_registration(self):
        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service'}

        self.service.on_registration_message(node_info)
        self.assertEqual(self.service.nodes_directory,
                         {node_info['node_id']: node_info})

        self.assertEqual(self.medium.send_registration_answer.call_count, 1)
        mock_call = self.medium.send_registration_answer.call_args
        self.assertEqual(mock_call, call(node_info))

        self.assertEqual(self.medium.connect_to_node.call_count, 1)
        mock_call = self.medium.connect_to_node.call_args
        self.assertEqual(mock_call, call(node_info))

        self.assertEqual(self.service.on_peer_join.call_count, 1)
        mock_call = self.service.on_peer_join.call_args
        self.assertEqual(mock_call, call(node_info))

    def test_register_twice(self):
        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service'}

        self.service.on_registration_message(node_info)
        self.assertEqual(self.service.nodes_directory,
                         {node_info['node_id']: node_info})
        self.medium.send_registration_answer.reset_mock()
        self.service.on_peer_join.reset_mock()

        self.service.on_registration_message(node_info)
        self.assertEqual(self.service.nodes_directory,
                         {node_info['node_id']: node_info})

        self.assertEqual(self.medium.send_registration_answer.call_count, 0)
        self.assertEqual(self.service.on_peer_join.call_count, 0)

    def test_call(self):
        node_info = {'node_id': 'sample', 'name': 'Sample Service'}

        self.service.on_registration_message(node_info)
        message = {'content': 'Coucou'}
        self.service.send(node_info['node_id'], message)

        self.assertEqual(self.medium.send.call_count, 1)
        mock_call = self.medium.send.call_args
        self.assertEqual(mock_call, call(node_info, message))

# class ServiceRegisterTestCase(unittest.TestCase):

#     def test_register_ressource_collection(self):
#         service = sample_service()()

#         collection = sample_collection()()
#         ressource_name = 'Test'
#         collection.ressource_name = ressource_name

#         service.register(collection)

#         # Check that collection is registered on our service...
#         self.assertEqual(service.ressources_collections, {ressource_name:
#             collection})
#         self.assertEqual(service.ressources, [ressource_name])

#         # And not in base Service
#         self.assertEqual(Service.ressources_collections, {})
#         self.assertEqual(Service.ressources, [])


# class ServiceCollectionTestCase(unittest.TestCase):

#     def setUp(self):
#         super(ServiceCollectionTestCase, self).__init__()
#         self.service = sample_service()()
#         self.collection = sample_collection()()
#         self.ressource_name = 'Test'
#         self.collection.ressource_name = self.ressource_name

#         self.service.register(self.collection)

#     def test_list(self):
#         self.collection.list.return_value = [42]

#         self.service.process_query(self.ressource_name, 'list',
#                                    callback=self.stop)
#         result = self.wait()

#         self.assertTrue(result['success'] == True)
#         self.assertEqual(result['data'], self.collection.list.return_value)
#         self.assertEqual(self.collection.list.call_args_list, [call()])

#     def test_process_query(self):
#         return_value = 'Ok'
#         mock = Mock(return_value=return_value)
#         self.collection.test = mock

#         kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
#         result = self.service.process_query(self.ressource_name, 'test',
#             kwargs)

#         self.assertEqual(mock.call_args_list, [call(**kwargs)])
#         self.assertEqual(result, {'success': True, 'data': return_value})

#     def test_process_query_failure(self):
#         return_value = False, 'Horrible Failure'
#         mock = Mock(return_value=return_value)
#         self.collection.test = mock

#         kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
#         result = self.service.process_query(self.ressource_name, 'test',
#             kwargs)

#         self.assertEqual(mock.call_args_list, [call(**kwargs)])
#         self.assertEqual(result, {'success': False, 'data': return_value[1]})

#     def test_query_return_dict(self):
#         return_value = {'arg1': 'Hi'}
#         mock = Mock(return_value=return_value)
#         self.collection.test = mock

#         kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
#         result = self.service.process_query(self.ressource_name, 'test',
#             kwargs)

#         self.assertEqual(mock.call_args_list, [call(**kwargs)])
#         self.assertEqual(result, {'success': True, 'data': return_value})

#     def test_query_return_empty_list(self):
#         return_value = []
#         mock = Mock(return_value=return_value)
#         self.collection.test = mock

#         kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
#         result = self.service.process_query(self.ressource_name, 'test',
#             kwargs)

#         self.assertEqual(mock.call_args_list, [call(**kwargs)])
#         self.assertEqual(result, {'success': True, 'data': return_value})

#     def test_process_query_bad_action(self):
#         kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
#         result = self.service.process_query(self.ressource_name, 'test',
#             kwargs)

#         self.assertEqual(result, {'success': False,
#             'data': 'The service can not satisfy the query'})

#     def test_process_query_error(self):
#         exception = Exception('Not a chance')

#         def side_effect(*args, **kwargs):
#             raise exception

#         mock = Mock(side_effect=side_effect)
#         self.collection.test = mock

#         kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
#         result = self.service.process_query(self.ressource_name, 'test',
#             kwargs)

#         self.assertEqual(mock.call_args_list, [call(**kwargs)])
#         self.assertEqual(result, {'success': False, 'message':
#             "Internal error: %s" % repr(exception)})
