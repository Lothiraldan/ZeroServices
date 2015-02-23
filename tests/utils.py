import asyncio

try:
    from unittest.mock import Mock, create_autospec
except ImportError:
    from mock import Mock, create_autospec

from uuid import uuid4
from functools import wraps
from copy import copy
from unittest import TestCase as unittestTestCase

from zeroservices.exceptions import ServiceUnavailable
from zeroservices.resources import (ResourceCollection, Resource,
                                    is_callable, ResourceService)
from zeroservices.medium import BaseMedium
from zeroservices.medium.memory import MemoryMedium
from zeroservices.discovery.memory import MemoryDiscoveryMedium
from zeroservices.memory import MemoryCollection, MemoryResource
from zeroservices import BaseService
from zeroservices.query import match


class TestCase(unittestTestCase):

    def assertItemsEqual(self, *args):
        if hasattr(self, 'assertCountEqual'):
            return self.assertCountEqual(*args)
        return super(TestCase, self).assertItemsEqual(*args)

    def assertDictIsSubset(self, subset, superset):
        for item in subset.items():
            self.assertIn(item, superset.items())


def test_medium():
    return Mock(spec_set=BaseMedium)


class TestResource(MemoryResource):

    @is_callable
    def custom_action(self, *arhs, **kwargs):
        return 42


class TestCollection(MemoryCollection):

    resource_class = TestResource

    @is_callable
    def custom_action(self, *args, **kwargs):
        return 42


def sample_collection(sample_resource_name):
    return TestCollection(sample_resource_name)


class TestService(BaseService):

    def __init__(self, *args, node_infos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_message_mock = Mock()
        self.on_event_mock = Mock()
        self.node_infos = node_infos or {}

    def service_info(self):
        base_infos = copy(self.node_infos)
        base_infos.update(super().service_info())
        return base_infos

    @asyncio.coroutine
    def on_message(self, *args, **kwargs):
        return self.on_message_mock(*args, **kwargs)

    @asyncio.coroutine
    def on_event(self, *args, **kwargs):
        return self.on_event_mock(*args, **kwargs)


def _create_test_service(name, node_infos, loop):
    medium = MemoryMedium(loop, MemoryDiscoveryMedium)
    service = TestService(name, medium, node_infos=node_infos)
    return service


class TestResourceService(ResourceService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_event_mock = Mock()

    @asyncio.coroutine
    def on_event(self, *args, **kwargs):
        return self.on_event_mock(*args, **kwargs)


def _create_test_resource_service(name, loop):
    medium = MemoryMedium(loop, MemoryDiscoveryMedium)
    service = TestResourceService(name, medium)
    return service


def _async_test(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.loop.is_running():
            coro = asyncio.coroutine(f)
            future = coro(self, *args, **kwargs)
            self.loop.run_until_complete(asyncio.wait_for(future, 2, loop=self.loop))
        else:
            return f(self, *args, **kwargs)
    return wrapper
