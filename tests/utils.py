try:
    from unittest.mock import Mock, create_autospec
except ImportError:
    from mock import Mock, create_autospec

from unittest import TestCase as unittestTestCase

from zeroservices.exceptions import ServiceUnavailable
from zeroservices.resources import (ResourceCollection, Resource,
                                     is_callable, ResourceService)
from zeroservices.medium import BaseMedium
from zeroservices import BaseService
from zeroservices.query import match


class TestCase(unittestTestCase):

    def assertItemsEqual(self, *args):
        if hasattr(self, 'assertCountEqual'):
            return self.assertCountEqual(*args)
        return super(TestCase, self).assertItemsEqual(*args)


def test_medium():
    return Mock(spec_set=BaseMedium)


class ServiceRegistry(object):
    SERVICES = {}
    SERVICES_RESSOURCES = {}


def sample_collection(sample_resource_name):

    collection = create_autospec(ResourceCollection, True)
    collection.resource_name = sample_resource_name

    return collection


def sample_resource():
    resource_class = create_autospec(Resource, True)
    resource_instance = create_autospec(Resource, True, instance=True)
    resource_class.return_value = resource_instance
    return resource_class, resource_instance


def sample_service():
    service = create_autospec(ResourceService, True, instance=True)
    return service


def base_resource():

    class BaseResource(Resource):

        def add_link(self):
            pass

        def create(self):
            pass

        def delete(self):
            pass

        def get(self):
            pass

        def patch(self):
            pass

    return BaseResource


class TestService(BaseService):

    def __init__(self, *args, **kwargs):
        super(TestService, self).__init__(*args, **kwargs)
        self.on_message = create_autospec(self.on_message, return_value=None)
        self.on_event = create_autospec(self.on_event, return_value=None)
