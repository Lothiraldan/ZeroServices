import unittest

from zeroservices import Service
from zeroservices.service import RessourceCollection, Ressource
from mock import Mock, call, create_autospec

from tornado.testing import AsyncTestCase


def sample_service():
    class SampleService(Service):
        pass
    return SampleService

def sample_collection():
    class SampleCollection(RessourceCollection):
        get = Mock()
        create = Mock()
        list = Mock()
    return SampleCollection

def sample_ressource():
    class SampleRessource(Ressource):
        pass
    return SampleRessource

class ServiceRegisterTestCase(unittest.TestCase):

    def test_register_ressource_collection(self):
        service = sample_service()()

        collection = sample_collection()()
        ressource_name = 'Test'
        collection.ressource_name = ressource_name

        service.register(collection)

        # Check that collection is registered on our service...
        self.assertEqual(service.ressources_collections, {ressource_name:
            collection})
        self.assertEqual(service.ressources, [ressource_name])

        # And not in base Service
        self.assertEqual(Service.ressources_collections, {})
        self.assertEqual(Service.ressources, [])


class ServiceCollectionTestCase(unittest.TestCase):

    def setUp(self):
        super(ServiceCollectionTestCase, self).__init__()
        self.service = sample_service()()
        self.collection = sample_collection()()
        self.ressource_name = 'Test'
        self.collection.ressource_name = self.ressource_name

        self.service.register(self.collection)

    def test_list(self):
        self.collection.list.return_value = [42]

        self.service.process_query(self.ressource_name, 'list',
                                   callback=self.stop)
        result = self.wait()

        self.assertTrue(result['success'] == True)
        self.assertEqual(result['data'], self.collection.list.return_value)
        self.assertEqual(self.collection.list.call_args_list, [call()])

    def test_process_query(self):
        return_value = 'Ok'
        mock = Mock(return_value=return_value)
        self.collection.test = mock

        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
        result = self.service.process_query(self.ressource_name, 'test',
            kwargs)

        self.assertEqual(mock.call_args_list, [call(**kwargs)])
        self.assertEqual(result, {'success': True, 'data': return_value})

    def test_process_query_failure(self):
        return_value = False, 'Horrible Failure'
        mock = Mock(return_value=return_value)
        self.collection.test = mock

        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
        result = self.service.process_query(self.ressource_name, 'test',
            kwargs)

        self.assertEqual(mock.call_args_list, [call(**kwargs)])
        self.assertEqual(result, {'success': False, 'data': return_value[1]})

    def test_query_return_dict(self):
        return_value = {'arg1': 'Hi'}
        mock = Mock(return_value=return_value)
        self.collection.test = mock

        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
        result = self.service.process_query(self.ressource_name, 'test',
            kwargs)

        self.assertEqual(mock.call_args_list, [call(**kwargs)])
        self.assertEqual(result, {'success': True, 'data': return_value})

    def test_query_return_empty_list(self):
        return_value = []
        mock = Mock(return_value=return_value)
        self.collection.test = mock

        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
        result = self.service.process_query(self.ressource_name, 'test',
            kwargs)

        self.assertEqual(mock.call_args_list, [call(**kwargs)])
        self.assertEqual(result, {'success': True, 'data': return_value})

    def test_process_query_bad_action(self):
        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
        result = self.service.process_query(self.ressource_name, 'test',
            kwargs)

        self.assertEqual(result, {'success': False,
            'data': 'The service can not satisfy the query'})

    def test_process_query_error(self):
        exception = Exception('Not a chance')

        def side_effect(*args, **kwargs):
            raise exception

        mock = Mock(side_effect=side_effect)
        self.collection.test = mock

        kwargs = {'arg1': 'arg1', 'arg2': 'arg2'}
        result = self.service.process_query(self.ressource_name, 'test',
            kwargs)

        self.assertEqual(mock.call_args_list, [call(**kwargs)])
        self.assertEqual(result, {'success': False, 'message':
            "Internal error: %s" % repr(exception)})
