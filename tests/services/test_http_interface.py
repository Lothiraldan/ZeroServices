import json

from zeroservices.services import get_http_interface, BasicAuth
from zeroservices.ressources import RessourceService
from tornado.testing import AsyncHTTPTestCase

try:
    from unittest.mock import Mock, call, sentinel, create_autospec
except ImportError:
    from mock import Mock, call, sentinel, create_autospec


class TestAuth(BasicAuth):

    def authorized(self, ressource, method):
        return True


class HttpInterfaceTestCase(AsyncHTTPTestCase):

    def setUp(self):
        self.service = create_autospec(RessourceService, True, instance=True)
        self.collection_name = "test_collection"
        super(HttpInterfaceTestCase, self).setUp()

    def get_app(self):
        port = self.get_http_port()
        self.app = get_http_interface(self.service, port=port,
            auth=TestAuth)
        return self.app


class HttpInterfaceMainTestCase(HttpInterfaceTestCase):

    def test_get_main(self):
        result = self.fetch(self.app.reverse_url("main"))
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body, b"Hello world from api")


class HttpInterfaceCollectionTestCase(HttpInterfaceTestCase):

    def setUp(self):
        super(HttpInterfaceCollectionTestCase, self).setUp()
        self.url = self.app.reverse_url("collection", self.collection_name)

    def test_get_on_collection(self):
        self.sentinel = "RETURN_VALUE"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body.decode('utf-8'), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="list", args={}))


class HttpInterfaceRessourceTestCase(HttpInterfaceTestCase):

    def setUp(self):
        super(HttpInterfaceRessourceTestCase, self).setUp()
        self.ressource_id = "1"
        self.url = self.app.reverse_url("ressource", self.collection_name,
            self.ressource_id)
        self.args = {'arg1': 'value1', 'arg2': 'value2'}
        self.body = json.dumps(self.args)

    def test_get_on_ressource(self):
        self.sentinel = "RETURN_VALUE"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body.decode('utf-8'), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="get", args={},
                 ressource_id=self.ressource_id))

    def test_post_on_ressource(self):
        self.sentinel = "RETURN_VALUE"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="POST", body=self.body)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body.decode('utf-8'), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="create", args=self.args,
                 ressource_id=self.ressource_id))

    def test_delete_on_ressource(self):
        self.sentinel = "RETURN_VALUE"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="DELETE")
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body.decode('utf-8'), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="delete", args={},
                 ressource_id=self.ressource_id))

    def test_patch_on_ressource(self):
        self.sentinel = "RETURN_VALUE"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="PATCH", body=self.body)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body.decode('utf-8'), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="patch", args=self.args,
                 ressource_id=self.ressource_id))
