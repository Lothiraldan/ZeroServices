import unittest

from zeroservices import RessourceService, RessourceCollection, RessourceWorker
from zeroservices.ressources import NoActionHandler, is_callable, Ressource
from zeroservices.exceptions import UnknownService, RessourceException
from .utils import test_medium, sample_collection, sample_ressource, base_ressource
from copy import deepcopy


try:
    from unittest.mock import call, Mock, patch, sentinel
except ImportError:
    from mock import call, Mock, patch, sentinel


class RessourceServiceTestCase(unittest.TestCase):

    def setUp(self):
        self.name = "TestService"
        self.medium = test_medium()
        self.service = RessourceService(self.name, self.medium)

    def test_service_info(self):
        service_info = self.service.service_info()
        self.assertEqual(service_info['name'], self.name)
        self.assertEqual(list(service_info['ressources']), [])
        self.assertEqual(service_info['node_type'], 'node')

    def test_on_join(self):
        ressource = 'TestRessource'

        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service',
                     'ressources': [ressource], 'node_type': 'node'}

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
        service_info = self.service.service_info()
        self.assertEqual(service_info['name'], self.name)
        self.assertEqual(list(service_info['ressources']), [ressource_name])

    def test_ressource_send(self):
        ressource = 'TestRessource'
        action = 'list'
        args = {'key': 'value', 'key2': 'value2'}
        ressource_id = 'UUID1'

        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service',
                     'ressources': [ressource], 'node_type': 'node'}

        self.service.on_registration_message(node_info)

        call_request = {'collection': ressource, 'action': action,
            'args': args, 'ressource_id': ressource_id}

        medium_mock_send = self.medium.send
        response = {'response': 'Foo'}
        medium_mock_send.return_value = {'success': True, 'data': response}

        result = self.service.send(**call_request)

        # Test that RessourceService.send return only data, not envelope
        self.assertEqual(result, response)

        # Check call
        self.assertEqual(medium_mock_send.call_count, 1)
        mock_call = medium_mock_send.call_args
        self.assertEqual(mock_call, call(node_info, call_request))

    def test_ressource_send_exception(self):
        ressource = 'TestRessource'
        action = 'list'
        args = {'key': 'value', 'key2': 'value2'}
        ressource_id = 'UUID1'

        self.service.on_peer_join = Mock()
        node_info = {'node_id': 'sample', 'name': 'Sample Service',
                     'node_type': 'node', 'ressources': [ressource]}

        self.service.on_registration_message(node_info)

        call_request = {'collection': ressource, 'action': action,
            'args': args, 'ressource_id': ressource_id}

        medium_mock_send = self.medium.send
        response = 'Error message'
        medium_mock_send.return_value = {'success': False, 'data': response}

        with self.assertRaises(RessourceException) as cm:
            self.service.send(**call_request)

        # Check exception
        self.assertEquals(cm.exception.error_message, response)

        # Check call
        self.assertEqual(medium_mock_send.call_count, 1)
        mock_call = medium_mock_send.call_args
        self.assertEqual(mock_call, call(node_info, call_request))

    def test_ressource_send_unknown_service(self):
        ressource = 'TestRessource'
        action = 'list'
        args = {'key': 'value', 'key2': 'value2'}
        ressource_id = 'UUID1'

        call_request = {'collection': ressource, 'action': action,
            'args': args, 'ressource_id': ressource_id}

        with self.assertRaises(UnknownService):
            self.service.send(**call_request)


class RessourceServiceFakeCollectionTestCase(unittest.TestCase):

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

    def test_ressource_send_local_collection(self):
        message_args = {'kwarg_1': 1, 'kwarg_2': 2, 'action': 'Foo'}
        message = {'collection': self.ressource_name}
        message.update(message_args)

        response = {'response': 'Foo'}
        self.collection.on_message.return_value = response

        self.assertEqual(self.service.send(**message),
                         {'success': True, 'data': response})

        self.assertEqual(self.collection.on_message.call_count, 1)
        default_message_type = "message"
        self.assertEqual(self.collection.on_message.call_args,
            call(**message_args))


class RessourceCollectionTestCase(unittest.TestCase):

    def setUp(self):
        self.ressource_name = 'Test'

        self.service = sentinel.service

        self.ressource_class, self.ressource_instance = sample_ressource()

        self.collection = RessourceCollection(self.ressource_class, 'ressource')
        self.collection.ressource_name = self.ressource_name
        self.collection.service = self.service


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

        collection = CustomCollection(self.ressource_class, 'ressource')
        self.assertEqual(collection.on_message(**query), return_value)

    def test_process_message_custom_action(self):
        class CustomCollection(RessourceCollection):

            def test(self):
                pass

        action_name = "test"
        query = {'action': action_name}

        collection = CustomCollection(self.ressource_class, 'ressource')

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

    def test_publish(self):
        publish_message = {'type': 'new', '_id': 'foo',
             'ressource_data': 'bar'}

        publish_mock = Mock()
        self.service.publish = publish_mock

        # Publish
        self.collection.publish(publish_message)

        # Check that collection added ressource_name to message
        publish_message = deepcopy(publish_message)
        publish_message.update({'ressource_name': self.ressource_name})

        self.assertEqual(publish_mock.call_args_list,
            [call(self.ressource_name, publish_message)])


class RessourceWorkerTestCase(unittest.TestCase):

    def setUp(self):
        self.name = "TestService"
        self.medium = test_medium()
        self.ressource_name = 'ressource'

        self.service = RessourceService(self.name, self.medium)
        collection = sample_collection(self.ressource_name)
        self.service.register_ressource(collection)

        self.worker_base_name = "sample_worker"

    def test_worker_info(self):

        worker = RessourceWorker(self.worker_base_name, self.medium)

        service_info = worker.service_info()
        self.assertEqual(service_info['node_type'], 'worker')
        self.assertEqual(service_info['ressources'], [])

        self.assertEqual(self.medium.register.call_count, 0)

    def test_worker_registration(self):

        ressource_name = self.ressource_name

        class WorkerSample(RessourceWorker):

            def __init__(self, *args, **kwargs):
                super(WorkerSample, self).__init__(*args, **kwargs)
                self.register(self.sample_action, ressource_name)

            def sample_action(self, ressource):
                pass

        worker = WorkerSample(self.worker_base_name, self.medium)

        service_info = worker.service_info()
        self.assertEqual(service_info['node_type'], 'worker')
        self.assertEqual(service_info['ressources'],
                         [self.ressource_name])

        self.assertEqual(self.medium.subscribe.call_count, 1)
        self.assertEqual(self.medium.subscribe.call_args,
                         call(self.ressource_name))

    def test_worker_registration_matcher(self):

        ressource_name = self.ressource_name
        matcher = {'key': 'value'}

        class WorkerSample(RessourceWorker):

            def __init__(self, *args, **kwargs):
                super(WorkerSample, self).__init__(*args, **kwargs)
                self.register(self.sample_action, ressource_name, **matcher)

            def sample_action(self, ressource):
                pass

        worker = WorkerSample(self.worker_base_name, self.medium)

        service_info = worker.service_info()
        self.assertEqual(service_info['node_type'], 'worker')
        self.assertEqual(service_info['ressources'],
                         [self.ressource_name])

        self.assertEqual(self.medium.subscribe.call_count, 1)
        self.assertEqual(self.medium.subscribe.call_args,
                         call(self.ressource_name))


class RessourceTestCase(unittest.TestCase):

    def setUp(self):
        self.ressource_name = 'Test'
        self.ressource_id = 'Test#1'

        self.service = sentinel.service

        self.collection = RessourceCollection(base_ressource(), 'ressource')
        self.collection.ressource_name = self.ressource_name
        self.collection.service = self.service

    def test_publish(self):
        publish_message = {'type': 'new', 'ressource_data': 'bar'}

        publish_mock = Mock()
        self.service.publish = publish_mock

        instance = self.collection.instantiate(ressource_id=self.ressource_id)
        instance.publish(publish_message)

        # Check that collection added ressource_name to message
        # And that ressource added ressource_id to message
        publish_message = deepcopy(publish_message)
        publish_message.update({'ressource_name': self.ressource_name,
            'ressource_id': self.ressource_id})

        self.assertEqual(publish_mock.call_args_list,
            [call(self.ressource_name, publish_message)])

