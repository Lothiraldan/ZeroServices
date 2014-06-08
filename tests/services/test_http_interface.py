import json

from zeroservices.services import get_http_interface
from zeroservices.ressources import RessourceService
from tornado.testing import AsyncHTTPTestCase

try:
    from unittest.mock import Mock, call, sentinel, create_autospec
except ImportError:
    from mock import Mock, call, sentinel, create_autospec

def test_auth(*args, **kwargs):
    def wrapper(handler):
        return handler
    return wrapper


class HttpInterfaceTestCase(AsyncHTTPTestCase):

    def setUp(self):
        self.service = create_autospec(RessourceService, True, instance=True)
        self.collection_name = "test_collection"
        self.args = {'arg1': 'value1', 'arg2': 'value2'}
        self.body = json.dumps(self.args)
        super(HttpInterfaceTestCase, self).setUp()

    def get_app(self):
        port = self.get_http_port()
        self.app = get_http_interface(self.service, port=port,
            auth_decorator=test_auth)
        return self.app

    def test_get_main(self):
        result = self.fetch(self.app.reverse_url("main"))
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body, b"Hello world from api")

    def test_get_on_collection(self):
        self.sentinel = "RETURN_VALUE"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.app.reverse_url("collection",
            self.collection_name))
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body.decode('utf-8'), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="list", args={}))

    def test_post_on_collection(self):
        self.sentinel = "RETURN_VALUE"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.app.reverse_url("collection",
            self.collection_name), method="POST", body=self.body)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body.decode('utf-8'), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="create", args=self.args))

