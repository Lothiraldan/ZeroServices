import unittest

from ..utils import test_medium, MemoryCollection
from . import _BaseCollectionTestCase

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class MemoryCollectionTestCase(_BaseCollectionTestCase):

    def setUp(self):
        super(MemoryCollectionTestCase, self).setUp()
        self.collection = MemoryCollection(self.ressource_name)
        self.collection.service = self.service
