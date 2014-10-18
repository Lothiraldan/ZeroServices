try:
    from unittest.mock import Mock, call
except ImportError:
    from mock import Mock, call

from copy import copy
from zeroservices import RessourceService, RessourceCollection, RessourceWorker
from .utils import test_medium, MemoryCollection
from .utils import MemoryMedium, TestService, TestCase
from .utils import test_medium, sample_collection, sample_ressource, base_ressource


class RuleTestCase(TestCase):
    pass


class RessourceWorkerUnitTestCase(TestCase):

    def setUp(self):
        self.ressource_name = 'TestCollection'

        self.medium1 = MemoryMedium('node1')
        self.worker1 = RessourceWorker('worker1', self.medium1)

    def test_no_rule(self):
        self.worker1.on_event('unknown_ressource',
                              {'ressource_name': 'unknown_ressource',
                               'ressource_data': {},
                               'ressource_id': 'doesn\'t matter',
                               'action': 'create'})

    def test_no_data(self):
        self.worker1.on_event('unknown_ressource',
                              {'ressource_name': 'unknown_ressource',
                               'ressource_id': 'doesn\'t matter',
                               'action': 'create'})


class RessourceWorkerTestCase(TestCase):

    def setUp(self):
        self.ressource_name = 'TestCollection'

        self.medium1 = MemoryMedium('node1')
        self.service1 = RessourceService('service1', self.medium1)
        self.collection1 = MemoryCollection(self.ressource_name)
        self.service1.register_ressource(self.collection1)

        self.medium2 = MemoryMedium('node2')

        self.patch = {'kwarg_3': 3}

        class SampleWorker(RessourceWorker):

            def __init__(self, name, medium, patch):
                super(SampleWorker, self).__init__(name, medium)
                self.patch = patch

            def sample_job(self, ressource_name, ressource_data, ressource_id,
                           action):
                if action == 'create' or action == 'periodic':
                    self.send(collection=ressource_name, action="patch",
                              ressource_id=ressource_id,
                              patch={'$set': self.patch})

        self.worker1 = SampleWorker('worker1', self.medium2, self.patch)

        self.callback = Mock()
        self.worker1.register(self.worker1.sample_job, self.ressource_name)

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
                         {self.ressource_name: [self.worker1.name]})

    def test_simple_job(self):
        self.service1.main()
        self.worker1.main()

        ressource_id = 'UUID1'
        ressource_data = {'kwarg_1': 1, 'kwarg_2': 2}
        message_args = {'ressource_data': ressource_data,
                        'ressource_id': ressource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.collection1.on_message(**query)

        expected_ressource = copy(ressource_data)
        expected_ressource.update(self.patch)

        updated_ressource_data = self.collection1.on_message(action='get',
                ressource_id=ressource_id)['ressource_data']
        self.assertEqual(
            updated_ressource_data,
            expected_ressource)

    def test_execute_job_on_startup(self):
        # Start the service
        self.service1.main()

        # Create the ressource
        ressource_id = 'UUID1'
        ressource_data = {'kwarg_1': 1, 'kwarg_2': 2}
        message_args = {'ressource_data': ressource_data,
                        'ressource_id': ressource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.collection1.on_message(**query)

        # Start the worker after ressource creation
        self.worker1.main()

        # Check that jobs have been scheduled
        self.assertEqual(len(self.medium2.callbacks), 1)
        self.medium2.call_callbacks()

        # Ressource should have been updated
        expected_ressource = copy(ressource_data)
        expected_ressource.update(self.patch)


        updated_ressource_data = self.collection1.on_message(action='get',
                ressource_id=ressource_id)['ressource_data']
        self.assertEqual(
            updated_ressource_data,
            expected_ressource)