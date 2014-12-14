from zeroservices.backend.mongodb import MongoDBCollection
from . import _BaseCollectionTestCase


class MongoDBCollectionTestCase(_BaseCollectionTestCase):

    def setUp(self):
        super(MongoDBCollectionTestCase, self).setUp()
        self.collection = MongoDBCollection(self.resource_name)
        self.collection.service = self.service

    def tearDown(self):
        self.collection.collection.drop()

