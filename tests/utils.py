try:
    from unittest.mock import Mock, create_autospec
except ImportError:
    from mock import Mock, create_autospec

from unittest import TestCase as unittestTestCase

from zeroservices.exceptions import ServiceUnavailable
from zeroservices.ressources import (RessourceCollection, Ressource,
                                     is_callable, RessourceService)
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


def sample_collection(sample_ressource_name):

    collection = create_autospec(RessourceCollection, True)
    collection.ressource_name = sample_ressource_name

    return collection


def sample_ressource():
    ressource_class = create_autospec(Ressource, True)
    ressource_instance = create_autospec(Ressource, True, instance=True)
    ressource_class.return_value = ressource_instance
    return ressource_class, ressource_instance


def sample_service():
    service = create_autospec(RessourceService, True, instance=True)
    return service


def base_ressource():

    class BaseRessource(Ressource):

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

    return BaseRessource


class TestService(BaseService):

    def __init__(self, *args, **kwargs):
        super(TestService, self).__init__(*args, **kwargs)
        self.on_message = create_autospec(self.on_message, return_value=None)
        self.on_event = create_autospec(self.on_event, return_value=None)
