import asyncio

try:
    from unittest.mock import Mock, call
except ImportError:
    from mock import Mock, call

from copy import copy
from zeroservices import ResourceWorker
from zeroservices.medium.memory import MemoryMedium
from zeroservices.discovery.memory import MemoryDiscoveryMedium
from zeroservices.memory import MemoryCollection
from .utils import TestCase, _create_test_resource_service, _async_test


class RuleTestCase(TestCase):
    pass


class ResourceWorkerUnitTestCase(TestCase):

    def setUp(self):
        self.resource_name = 'TestCollection'

        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

        self.medium1 = MemoryMedium(self.loop, MemoryDiscoveryMedium, node_id='node1')
        self.worker1 = ResourceWorker('worker1', self.medium1)
        self.mock = Mock()
        self.worker1.register(self.mock, 'resource2')

    def tearDown(self):
        self.medium1.close()
        self.worker1.close()
        self.loop.stop()
        self.loop.close()
        self.medium1.check_leak()
        self.worker1.medium.check_leak()

    def test_no_rule(self):
        ''' Check that it doesn't raise an exception
        '''
        yield from self.worker1.on_event('resource1',
                                         **{'resource_name': 'resource1',
                                            'resource_data': {},
                                            'resource_id': 'doesn\'t matter',
                                            'action': 'create'})
        self.assertEqual(self.mock.call_count, 0)


class ResourceWorkerTestCase(TestCase):

    def setUp(self):
        self.resource_name = 'TestCollection'

        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

        self.service1 = _create_test_resource_service('test_service', self.loop)
        self.collection1 = MemoryCollection(self.resource_name)
        self.service1.register_resource(self.collection1)

        self.medium2 = MemoryMedium(self.loop, MemoryDiscoveryMedium, 'node2')

        self.patch = {'kwarg_1': 42}

        class SampleWorker(ResourceWorker):

            def __init__(self, name, medium, patch):
                super(SampleWorker, self).__init__(name, medium)
                self.patch = patch

            def sample_job(self, resource_name, resource_data, resource_id,
                           action):
                yield from self.send(collection_name=resource_name, action="patch",
                                     resource_id=resource_id,
                                     patch={'$set': self.patch})

        self.worker1 = SampleWorker('worker1', self.medium2, self.patch)

        self.callback = Mock()
        self.worker1.register(self.worker1.sample_job, self.resource_name,
                              kwarg_1=1)

    def tearDown(self):
        self.service1.close()
        self.worker1.close()
        self.medium2.close()
        self.loop.stop()
        self.loop.close()
        self.service1.medium.check_leak()
        self.worker1.medium.check_leak()
        self.medium2.check_leak()

    @_async_test
    def test_join(self):
        yield from self.service1.start()
        yield from self.worker1.start()

        self.assertItemsEqual(self.worker1.get_known_nodes(),
                              [self.service1.medium.node_id])

        self.assertItemsEqual(self.service1.get_known_nodes(),
                              [])
        self.assertEqual(self.service1.get_known_worker_nodes(),
                         {self.resource_name: [self.worker1.name]})

    @_async_test
    def test_simple_job(self):
        yield from self.service1.start()
        yield from self.worker1.start()

        resource_id = 'UUID1'
        resource_data = {'kwarg_1': 1, 'kwarg_2': 2}
        message_args = {'resource_data': resource_data,
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        # Create the resource
        yield from self.collection1.on_message(**query)

        expected_resource = copy(resource_data)
        expected_resource.update(self.patch)

        updated_resource_data = yield from self.collection1.on_message(action='get',
                                                                       resource_id=resource_id)
        updated_resource_data = updated_resource_data['resource_data']
        self.assertEqual(
            updated_resource_data,
            expected_resource)

    @_async_test
    def test_no_data(self):
        yield from self.service1.start()

        # Create the resource
        resource_id = 'UUID1'
        resource_data = {'kwarg_1': 1, 'kwarg_2': 2, 'kwarg_4': 4}
        message_args = {'resource_data': resource_data,
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        yield from self.collection1.on_message(**query)

        # Start the worker and send it a patch event
        yield from self.worker1.start()

        # Update the resource
        resource_id = 'UUID1'

        patch = {'kwarg_2': 3}
        query = {'$set': patch}

        message = {'action': 'patch', 'resource_id': resource_id,
                   'patch': query}
        yield from self.collection1.on_message(**message)

        expected_resource = copy(resource_data)
        expected_resource.update(self.patch)

        updated_resource_data = yield from self.collection1.on_message(action='get',
                resource_id=resource_id)
        updated_resource_data = updated_resource_data['resource_data']
        self.assertEqual(
            updated_resource_data,
            expected_resource)

    @_async_test
    def test_execute_job_on_startup(self):
        # Start the service
        yield from self.service1.start()

        # Create the resource
        resource_id = 'UUID1'
        resource_data = {'kwarg_1': 1, 'kwarg_2': 2}
        message_args = {'resource_data': resource_data,
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        yield from self.collection1.on_message(**query)

        # Start the worker after resource creation
        yield from self.worker1.start()

        # Check that jobs have been scheduled
        self.assertEqual(len(self.medium2.callbacks), 1)
        yield from self.medium2.call_callbacks()

        # Resource should have been updated
        expected_resource = copy(resource_data)
        expected_resource.update(self.patch)

        updated_resource_data = yield from self.collection1.on_message(action='get',
                resource_id=resource_id)
        updated_resource_data = updated_resource_data['resource_data']
        self.assertEqual(
            updated_resource_data,
            expected_resource)
