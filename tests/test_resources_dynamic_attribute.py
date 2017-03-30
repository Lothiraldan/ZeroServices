import asyncio

from zeroservices import ResourceService
from zeroservices.resources import dynamic_attribute
from zeroservices.medium.memory import MemoryMedium
from zeroservices.memory import MemoryResource, MemoryCollection
from zeroservices.discovery.memory import MemoryDiscoveryMedium
from .utils import TestCase, _async_test


try:
    from unittest.mock import call, Mock, patch, sentinel
except ImportError:
    from mock import call, Mock, patch, sentinel


class DynamicAttributeDoubleSumResource(MemoryResource):

    dynamic_attributes = ['double_sum']

    @dynamic_attribute('sum')
    def double_sum(self, sum):
        return sum * 2


class DynamicAttributeFooBarSumResource(MemoryResource):

    dynamic_attributes = ['foo_bar_sum']

    @dynamic_attribute('foo', 'bar')
    def foo_bar_sum(self, foo, bar):
        return foo + bar


class DynamicAttributeSubResource(MemoryResource):

    dynamic_attributes = ['sub_resource_sum']

    @dynamic_attribute('sub.sum')
    def sub_resource_sum(self, sub_sum):
        return sum(sub_sum)


class ResourceDynamicAttributeTestCase(TestCase):

    def setUp(self):
        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()
        self.resource_name = 'Test'

        self.medium = MemoryMedium(self.loop, MemoryDiscoveryMedium, 'Node')
        self.service = ResourceService('Service', self.medium)

        self.collection = MemoryCollection('resource', DynamicAttributeDoubleSumResource)
        self.collection.resource_name = self.resource_name
        self.collection.service = self.service

    def set_resource_class(self, resource_class):
        self.collection.resource_class = resource_class

    @_async_test
    def test_resource_create(self):
        resource_id = 'UUID1'
        message_args = {'resource_data': {'sum': 1},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        result = yield from self.collection.on_message(**query)
        self.assertEquals(result,
                          {'resource_id': resource_id})

        expected_published_message = [
            ('Test.create.UUID1',
            {'action': 'create',
             'resource_data': {'sum': 1, 'double_sum': 2},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)

    @_async_test
    def test_sub_resource_dependencie_create(self):
        self.set_resource_class(DynamicAttributeSubResource)

        resource_id = 'UUID1'
        message_args = {'resource_data': {'sub': {'sum': [42, 24]}},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        result = yield from self.collection.on_message(**query)
        self.assertEquals(result,
                          {'resource_id': resource_id})

        expected_published_message = [
            ('Test.create.UUID1',
            {'action': 'create',
             'resource_data': {'sub': {'sum': [42, 24]}, 'sub_resource_sum': 66},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)

    @_async_test
    def test_resource_create_missing_requirement(self):
        """
        Check that if one dependencie is missing, it doesn't fails
        """
        resource_id = 'UUID1'
        message_args = {'resource_data': {'foo': 'bar'},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        result = yield from self.collection.on_message(**query)
        self.assertEquals(result,
                          {'resource_id': resource_id})

        expected_published_message = [
            ('Test.create.UUID1',
            {'action': 'create',
             'resource_data': {'foo': 'bar'},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)

    @_async_test
    def test_resource_update(self):
        """
        Check that dynamic attributes are recomputed on update
        """
        resource_id = 'UUID1'
        message_args = {'resource_data': {'sum': 1, 'foo': 'bar'},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        result = yield from self.collection.on_message(**query)
        self.assertEquals(result,
                          {'resource_id': resource_id})

        # Update
        message_args = {'patch': {'$set': {'sum': 3}},
                        'resource_id': resource_id}
        query = {'action': 'patch'}
        query.update(message_args)

        self.medium.reset_published_messages()

        result = yield from self.collection.on_message(**query)
        self.assertEqual(result,
                         {'sum': 3, 'double_sum': 6, 'foo': 'bar'})

        expected_published_message = [
            ('Test.patch.UUID1',
            {'action': 'patch',
             'patch': {'$set': {'sum': 3, 'double_sum': 6}},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)

    @_async_test
    def test_resource_update_multiple_requirements(self):
        '''update only one requirement
        '''
        self.set_resource_class(DynamicAttributeFooBarSumResource)
        resource_id = 'UUID1'
        message_args = {'resource_data': {'foo': 1, 'bar': 1},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        result = yield from self.collection.on_message(**query)
        self.assertEquals(result,
                          {'resource_id': resource_id})

        # Update
        message_args = {'patch': {'$set': {'foo': 3}},
                        'resource_id': resource_id}
        query = {'action': 'patch'}
        query.update(message_args)

        self.medium.reset_published_messages()

        result = yield from self.collection.on_message(**query)
        self.assertEqual(result,
                         {'foo': 3, 'foo_bar_sum': 4, 'bar': 1})

        expected_published_message = [
            ('Test.patch.UUID1',
            {'action': 'patch',
             'patch': {'$set': {'foo': 3, 'foo_bar_sum': 4}},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)

    @_async_test
    def test_sub_resource_dependencie_update(self):
        self.set_resource_class(DynamicAttributeSubResource)

        resource_id = 'UUID1'
        message_args = {'resource_data': {'sub': {'sum': [42]}},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        result = yield from self.collection.on_message(**query)
        self.assertEquals(result,
                          {'resource_id': resource_id})

        # Update
        message_args = {'patch': {'$set': {'sub.sum': [24]}},
                        'resource_id': resource_id}
        query = {'action': 'patch'}
        query.update(message_args)

        self.medium.reset_published_messages()

        result = yield from self.collection.on_message(**query)
        self.assertEqual(result,
                         {'sub': {'sum': [24]}, 'sub_sum': [24]})

        expected_published_message = [
            ('Test.patch.UUID1',
            {'action': 'patch',
             'patch': {'$set': {'sub.sum': [24], 'sub_sum': [24]}},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)
