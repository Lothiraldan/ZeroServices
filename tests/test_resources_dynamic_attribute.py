import sys
import unittest

from zeroservices import ResourceService, ResourceCollection, ResourceWorker
from zeroservices.resources import NoActionHandler, is_callable, Resource, dynamic_attribute
from zeroservices.exceptions import UnknownService, ResourceException
from zeroservices.memory import MemoryResource, MemoryCollection, MemoryMedium
from .utils import test_medium, sample_collection, sample_resource, base_resource, TestCase
from copy import deepcopy


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
        return foo +bar



class ResourceDynamicAttributeTestCase(TestCase):

    def setUp(self):
        self.resource_name = 'Test'

        self.medium = MemoryMedium('Node')
        self.service = ResourceService('Service', self.medium)

        self.collection = MemoryCollection('resource', DynamicAttributeDoubleSumResource)
        self.collection.resource_name = self.resource_name
        self.collection.service = self.service

    def set_resource_class(self, resource_class):
        self.collection.resource_class = resource_class

    def test_resource_create(self):
        resource_id = 'UUID1'
        message_args = {'resource_data': {'sum': 1},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.medium.published_messages = []

        self.assertEquals(self.collection.on_message(**query),
                          {'resource_id': resource_id})

        expected_published_message = [
            ('Test.create.UUID1',
            {'action': 'create',
             'resource_data': {'sum': 1, 'double_sum': 2},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)

    def test_resource_create_missing_requirement(self):
        resource_id = 'UUID1'
        message_args = {'resource_data': {'foo': 'bar'},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.medium.published_messages = []

        self.assertEquals(self.collection.on_message(**query),
                          {'resource_id': resource_id})

        expected_published_message = [
            ('Test.create.UUID1',
            {'action': 'create',
             'resource_data': {'foo': 'bar'},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)

    def test_resource_update(self):
        resource_id = 'UUID1'
        message_args = {'resource_data': {'sum': 1, 'foo': 'bar'},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.assertEquals(self.collection.on_message(**query),
                          {'resource_id': resource_id})

        # Update
        message_args = {'patch': {'$set': {'sum': 3}},
                        'resource_id': resource_id}
        query = {'action': 'patch'}
        query.update(message_args)

        self.medium.published_messages = []

        self.assertEqual(self.collection.on_message(**query),
                         {'sum': 3, 'double_sum': 6, 'foo': 'bar'})

        expected_published_message = [
            ('Test.patch.UUID1',
            {'action': 'patch',
             'patch': {'$set': {'sum': 3, 'double_sum': 6}},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)

    def test_resource_update_multiple_requirements(self):
        '''update only one requirement
        '''
        self.set_resource_class(DynamicAttributeFooBarSumResource)
        resource_id = 'UUID1'
        message_args = {'resource_data': {'foo': 1, 'bar': 1},
                        'resource_id': resource_id}
        query = {'action': 'create'}
        query.update(message_args)

        self.assertEquals(self.collection.on_message(**query),
                          {'resource_id': resource_id})

        # Update
        message_args = {'patch': {'$set': {'foo': 3}},
                        'resource_id': resource_id}
        query = {'action': 'patch'}
        query.update(message_args)

        self.medium.published_messages = []

        self.assertEqual(self.collection.on_message(**query),
                         {'foo': 3, 'foo_bar_sum': 4, 'bar': 1})

        expected_published_message = [
            ('Test.patch.UUID1',
            {'action': 'patch',
             'patch': {'$set': {'foo': 3, 'foo_bar_sum': 4}},
             'resource_id': 'UUID1',
             'resource_name': 'Test'})]
        self.assertEquals(self.medium.published_messages,
                          expected_published_message)
