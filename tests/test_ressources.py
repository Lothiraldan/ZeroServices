import unittest

from zeroservices import RessourceService, RessourceCollection
from zeroservices.ressources import NoActionHandler, is_callable
from utils import test_medium, sample_collection, sample_ressource
from mock import call, Mock, patch, sentinel


class RessourceServiceTestCase(unittest.TestCase):

    def setUp(self):
        self.name = "TestService"
        self.medium = test_medium()
        self.service = RessourceService(self.name, self.medium)

    def test_service_info(self):
        self.assertEqual(self.service.service_info(), {'name': self.name,
                                                       'ressources': []})

    def test_on_join(self):
        ressource = 'TestRessource'

        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service',
                     'ressources': [ressource]}

        self.service.on_registration_message(node_info)
        self.assertEqual(self.service.nodes_directory,
                         {node_info['node_id']: node_info})
        self.assertEqual(self.service.ressources_directory,
                         {ressource: node_info['node_id']})

        self.assertEqual(self.medium.send_registration_answer.call_count, 1)
        mock_call = self.medium.send_registration_answer.call_args
        self.assertEqual(mock_call, call(node_info))

        self.assertEqual(self.medium.connect_to_node.call_count, 1)
        mock_call = self.medium.connect_to_node.call_args
        self.assertEqual(mock_call, call(node_info))

        self.assertEqual(self.service.on_peer_join.call_count, 1)
        mock_call = self.service.on_peer_join.call_args
        self.assertEqual(mock_call, call(node_info))

    def test_ressource_registration(self):
        ressource_name = 'TestCollection'
        collection = sample_collection(ressource_name)

        self.service.register_ressource(collection)
        expected = {'name': self.name, 'ressources': [ressource_name]}
        self.assertEqual(self.service.service_info(), expected)

    def test_ressource_call(self):
        ressource = 'TestRessource'
        action = 'list'
        args = {'key': 'value', 'key2': 'value2'}
        ressource_id = 'UUID1'

        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service',
                     'ressources': [ressource]}

        self.service.on_registration_message(node_info)

        call_request = {'collection': ressource, 'action': action,
            'args': args, 'ressource_id': ressource_id}

        self.service.send(**call_request)

        self.assertEqual(self.medium.send.call_count, 1)
        mock_call = self.medium.send.call_args
        self.assertEqual(mock_call, call(node_info, call_request))

class RessourceCollectionTestCase(unittest.TestCase):

    def setUp(self):
        self.name = "TestService"
        self.medium = test_medium()
        self.service = RessourceService(self.name, self.medium)

        self.ressource_name = 'TestCollection'
        self.collection = sample_collection(self.ressource_name)
        self.service.register_ressource(self.collection)

    def test_ressource_query(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2, 'action': 'Foo'}
        message = {'collection': self.ressource_name}
        message.update(message_args)

        response = {'response': 'Foo'}
        self.collection.on_message.return_value = response

        self.assertEqual(self.service.on_message(**message),
                         {'success': True, 'data': response})

        self.assertEqual(self.collection.on_message.call_count, 1)
        self.assertEqual(self.collection.on_message.call_args, call(**message_args))

    def test_ressource_query_no_matching_collection(self):
        ressource_name = 'OtherRessource'

        message_args = {'kwarg_1': 1, 'kwarg_2': 2}
        message = {'collection': ressource_name}
        message.update(message_args)

        self.assertNotEquals(ressource_name, self.ressource_name)

        response = {'response': 'Foo'}
        self.collection.on_message.return_value = response

        result = self.service.on_message(**message)

        self.assertEqual(self.collection.on_message.call_count, 0)

        self.assertEqual(result['success'], False)
        self.assertTrue(ressource_name in result['message'])

    def test_ressource_query_exception(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2, 'action': 'Bar'}
        message = {'collection': self.ressource_name}
        message.update(message_args)

        error_message = 'OUPS'
        self.collection.on_message.side_effect = Exception(error_message)

        self.assertEqual(self.service.on_message(**message),
                         {'success': False, 'data': error_message})

        self.assertEqual(self.collection.on_message.call_count, 1)


class RessourceCollectionTestCase(unittest.TestCase):

    def setUp(self):
        self.ressource_name = 'Test'

        self.service = sentinel.service

        self.collection = RessourceCollection()
        self.collection.ressource_name = self.ressource_name
        self.collection.service = self.service

        self.ressource_class, self.ressource_instance = sample_ressource()
        self.collection.ressource_class = self.ressource_class

    def test_process_message(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2}
        query = {'action': 'list'}
        query.update(message_args)

        with patch.object(self.collection, 'list') as mock:
            return_value = [42]
            mock.return_value = return_value

            self.assertEqual(self.collection.on_message(**query),
                             return_value)

        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args, call(**message_args))

    def test_process_message_bad_action(self):
        return_value = 42

        class CustomCollection(RessourceCollection):

            @is_callable
            def test(self):
                return return_value

        action_name = "test"
        query = {'action': action_name}

        collection = CustomCollection()
        self.assertEqual(collection.on_message(**query), return_value)

    def test_process_message_custom_action(self):
        class CustomCollection(RessourceCollection):

            def test(self):
                pass

        action_name = "test"
        query = {'action': action_name}

        collection = CustomCollection()

        with self.assertRaises(NoActionHandler):
            collection.on_message(**query)

    def test_process_message_no_handler(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2}
        query = {'action': 'unknown'}
        query.update(message_args)

        with self.assertRaises(NoActionHandler):
            self.collection.on_message(**query)

    def test_process_message_create(self):
        ressource_id = 'UUID1'
        message_args = {'ressource_data': {'kwarg_1': 1, 'kwarg_2': 2},
                        'ressource_id': ressource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.ressource_instance.create.return_value = sentinel.ressource

        self.assertEqual(self.collection.on_message(**query),
                         sentinel.ressource)

        self.ressource_class.assert_called_once_with(
            ressource_collection=self.collection,
            ressource_id=ressource_id, service=self.service)

        del message_args['ressource_id']
        self.ressource_instance.create.assert_called_once_with(**message_args)

    def test_process_message_patch(self):
        ressource_id = 'UUID1'
        message_args = {'patch': {'kwarg_1': 1, 'kwarg_2': 2},
                        'ressource_id': ressource_id}
        query = {'action': 'patch'}
        query.update(message_args)

        self.ressource_instance.patch.return_value = sentinel.ressource

        self.assertEqual(self.collection.on_message(**query),
                         sentinel.ressource)

        self.ressource_class.assert_called_once_with(
            ressource_collection=self.collection,
            ressource_id=ressource_id, service=self.service)

        del message_args['ressource_id']
        self.ressource_instance.patch.assert_called_once_with(**message_args)


    def test_process_message_delete(self):
        ressource_id = 'UUID1'
        message_args = {'ressource_id': ressource_id}
        query = {'action': 'delete'}
        query.update(message_args)

        self.ressource_instance.delete.return_value = sentinel.ressource

        self.assertEqual(self.collection.on_message(**query), sentinel.ressource)

        self.ressource_class.assert_called_once_with(
            ressource_collection=self.collection,
            ressource_id=ressource_id, service=self.service)

        del message_args['ressource_id']
        self.ressource_instance.delete.assert_called_once_with()
