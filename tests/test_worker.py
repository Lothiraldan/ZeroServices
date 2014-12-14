try:
    from unittest.mock import Mock, call
except ImportError:
    from mock import Mock, call

from copy import copy
from zeroservices import ResourceService, ResourceCollection, ResourceWorker
from zeroservices.memory import MemoryMedium, MemoryCollection
from .utils import (test_medium, sample_collection, sample_resource,
    base_resource, TestCase, TestService)


class RuleTestCase(TestCase):
    pass


class ResourceWorkerUnitTestCase(TestCase):

    def setUp(self):
        self.resource_name = 'TestCollection'

        self.medium1 = MemoryMedium('node1')
        self.worker1 = ResourceWorker('worker1', self.medium1)
        self.mock = Mock()
        self.worker1.register(self.mock, 'resource2')

    def test_no_rule(self):
        self.worker1.on_event('resource1',
                              {'resource_name': 'resource1',
                               'resource_data': {},
                               'resource_id': 'doesn\'t matter',
                               'action': 'create'})


class ResourceWorkerTestCase(TestCase):

    def setUp(self):
        self.resource_name = 'TestCollection'

        self.medium1 = MemoryMedium('node1')
        self.service1 = ResourceService('service1', self.medium1)
        self.collection1 = MemoryCollection(self.resource_name)
        self.service1.register_resource(self.collection1)

        self.medium2 = MemoryMedium('node2')

        self.patch = {'kwarg_1': 42}

        class SampleWorker(ResourceWorker):

            def __init__(self, name, medium, patch):
                super(SampleWorker, self).__init__(name, medium)
                self.patch = patch

            def sample_job(self, resource_name, resource_data, resource_id,
                           action):
                print "Here ?"
                self.send(collection=resource_name, action="patch",
                          resource_id=resource_id,
                          patch={'$set': self.patch})

        self.worker1 = SampleWorker('worker1', self.medium2, self.patch)

        self.callback = Mock()
        self.worker1.register(self.worker1.sample_job, self.resource_name,
            kwarg_1=1)

    def tearDown(self):
        self.service1.close()
        self.worker1.close()

    def test_join(self):
        self.service1.main()
        self.worker1.main()

        self.assertItemsEqual(self.worker1.get_known_nodes(),
                              ['node1'])

        self.assertItemsEqual(self.service1.get_known_nodes(),
                              [])
        self.assertEqual(self.service1.get_known_worker_nodes(),
                         {self.resource_name: [self.worker1.name]})

    def test_simple_job(self):
        self.service1.main()
        self.worker1.main()

        resource_id = 'UUID1'
        resource_data = {'kwarg_1': 1, 'kwarg_2': 2}
        message_args = {'resource_data': resource_data,
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.collection1.on_message(**query)

        expected_resource = copy(resource_data)
        expected_resource.update(self.patch)

        updated_resource_data = self.collection1.on_message(action='get',
                resource_id=resource_id)['resource_data']
        self.assertEqual(
            updated_resource_data,
            expected_resource)

    def test_no_data(self):
        self.service1.main()

        # Create the resource

        resource_id = 'UUID1'
        resource_data = {'kwarg_1': 1, 'kwarg_2': 2, 'kwarg_4': 4}
        message_args = {'resource_data': resource_data,
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.collection1.on_message(**query)

        # Start the worker and send it a patch event
        self.worker1.main()

        self.worker1.on_event(self.resource_name,
                              {'resource_name': self.resource_name,
                               'resource_id': resource_id,
                               'action': 'patch',
                               'patch': self.patch})

        expected_resource = copy(resource_data)
        expected_resource.update(self.patch)

        updated_resource_data = self.collection1.on_message(action='get',
                resource_id=resource_id)['resource_data']
        self.assertEqual(
            updated_resource_data,
            expected_resource)

    def test_execute_job_on_startup(self):
        # Start the service
        self.service1.main()

        # Create the resource
        resource_id = 'UUID1'
        resource_data = {'kwarg_1': 1, 'kwarg_2': 2}
        message_args = {'resource_data': resource_data,
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.collection1.on_message(**query)

        # Start the worker after resource creation
        self.worker1.main()

        # Check that jobs have been scheduled
        self.assertEqual(len(self.medium2.callbacks), 1)
        self.medium2.call_callbacks()

        # Resource should have been updated
        expected_resource = copy(resource_data)
        expected_resource.update(self.patch)


        updated_resource_data = self.collection1.on_message(action='get',
                resource_id=resource_id)['resource_data']
        self.assertEqual(
            updated_resource_data,
            expected_resource)
