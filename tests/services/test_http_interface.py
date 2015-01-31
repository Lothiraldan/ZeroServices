import json
import sys

from base64 import b64encode
from zeroservices.services import get_http_interface, BasicAuth
from zeroservices.resources import ResourceService
from zeroservices.exceptions import UnknownService
from tornado.testing import AsyncHTTPTestCase
from tornado.websocket import websocket_connect, WebSocketClientConnection

try:
    from unittest.mock import Mock, call, sentinel, create_autospec
except ImportError:
    from mock import Mock, call, sentinel, create_autospec


class TestAuth(BasicAuth):

    def authorized(self, handler, resource, method):
        return True


class TestBasicAuth(BasicAuth):

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def check_auth(self, username, password, resource, method):
        return username == self.username and password == self.password


class HttpInterfaceTestCase(AsyncHTTPTestCase):

    def setUp(self):
        self.service = create_autospec(ResourceService, True, instance=True)
        self.collection_name = "test_collection"
        self.old_argv = sys.argv
        sys.argv = []
        super(HttpInterfaceTestCase, self).setUp()

    def tearDown(self):
        sys.argv = self.old_argv

    def get_app(self):
        port = self.get_http_port()
        self.app = get_http_interface(self.service, port=port,
            auth=self.get_auth())
        return self.app

    def get_auth(self):
        return TestAuth()


class HttpInterfaceMainTestCase(HttpInterfaceTestCase):

    def test_get_main(self):
        result = self.fetch(self.app.reverse_url("main"))
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body, b"Hello world from api")


class HttpInterfaceCollectionTestCase(HttpInterfaceTestCase):

    def setUp(self):
        super(HttpInterfaceCollectionTestCase, self).setUp()
        self.url = self.app.reverse_url("collection", self.collection_name)
        self.collection_bad_url = self.app.reverse_url("collection", "bad")

    def test_get_on_collection(self):
        self.sentinel = [{'_id': '#1'}]
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="list"))

    def test_get_on_unknown_collection(self):
        self.service.send.side_effect = UnknownService('unknown service bad')

        result = self.fetch(self.collection_bad_url)
        self.assertEqual(result.code, 404)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         {'error': 'unknown service bad'})


    def test_post_create_on_collection(self):
        resource = {'resource_id': '#1', 'resource_data': {}}
        self.service.send.return_value = resource

        # Include empty body just for the tests :(
        body = json.dumps(resource)
        result = self.fetch(self.url, method="POST", body=body)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')), resource)

        self.assertEqual(self.service.send.call_args,
                         call(collection=self.collection_name,
                              action='create', resource_data={},
                              resource_id=resource['resource_id']))


    def test_custom_action_on_collection(self):
        custom_action = 'custom_action'
        self.sentinel = [{'_id': '#1'}]
        self.service.send.return_value = self.sentinel

        # Include empty body just for the tests :(
        result = self.fetch(self.url, method="POST", body='',
                            headers={'X-CUSTOM-ACTION': 'custom_action'})
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action=custom_action))


class HttpInterfaceResourceTestCase(HttpInterfaceTestCase):

    def setUp(self):
        super(HttpInterfaceResourceTestCase, self).setUp()
        self.resource_id = "1"
        self.url = self.app.reverse_url("resource", self.collection_name,
            self.resource_id)
        self.args = {'arg1': 'value1', 'arg2': 'value2'}
        self.body = json.dumps(self.args)

    def test_get_on_resource(self):
        self.sentinel = {'_id': self.resource_id}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="get",
                 resource_id=self.resource_id))

    def test_post_on_resource(self):
        self.sentinel = {'_id': self.resource_id}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="POST", body=self.body)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="create",
                 resource_id=self.resource_id, **self.args))

    def test_delete_on_resource(self):
        self.sentinel = "OK"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="DELETE")
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="delete",
                 resource_id=self.resource_id))

    def test_patch_on_resource(self):
        self.sentinel = {'_id': '#1'}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="PATCH", body=self.body)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="patch",
                 resource_id=self.resource_id, **self.args))

    def test_custom_action_on_resource(self):
        custom_action = 'custom_action'
        self.sentinel = {'_id': '#1'}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="POST",
                            headers={'X-CUSTOM-ACTION': 'custom_action'},
                            body=self.body)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name,
                 resource_id=self.resource_id,  action=custom_action,
                 **self.args))


class HttpInterfaceResourceIdSlash(HttpInterfaceTestCase):

    def setUp(self):
        super(HttpInterfaceResourceIdSlash, self).setUp()
        self.resource_id = "feature/test"
        self.url = self.app.reverse_url("resource", self.collection_name,
            self.resource_id)

    def test_get(self):
        self.sentinel = {'_id': self.resource_id}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url)
        self.assertEqual(result.code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="get",
                 resource_id=self.resource_id))



class HttpInterfaceBasicAuthTestCase(HttpInterfaceTestCase):

    def setUp(self):
        self.username = "username"
        self.password = "VERYSECURETOKEN"
        super(HttpInterfaceBasicAuthTestCase, self).setUp()

    def get_auth(self):
        return TestBasicAuth(self.username, self.password)

    def get_auth_header(self, username, password=''):
        if password:
            auth_header = '{0}:{1}'.format(username, password)
        else:
            auth_header = username
        return b64encode(auth_header.encode('utf-8')).decode('utf-8')

    def test_without_header(self):
        result = self.fetch(self.app.reverse_url("main"))
        self.assertEqual(result.code, 401)
        self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

    def test_empty_header(self):
        url = self.app.reverse_url("main")
        result = self.fetch(url, headers={'Authorization': ''})

        self.assertEqual(result.code, 401)
        self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

    def test_bad_header(self):
        url = self.app.reverse_url("main")
        result = self.fetch(url, headers={'Authorization': 'BadHeader'})

        self.assertEqual(result.code, 401)
        self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

    def test_bad_header_value(self):
        url = self.app.reverse_url("main")
        result = self.fetch(url, headers={'Authorization': 'Basic NOPE=+/'})

        self.assertEqual(result.code, 401)
        self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

    def test_bad_header_value(self):
        url = self.app.reverse_url("main")
        result = self.fetch(url, headers={'Authorization': 'Basic NOPE=+/'})

        self.assertEqual(result.code, 401)
        self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

    def test_bad_header_not_b64(self):
        url = self.app.reverse_url("main")
        result = self.fetch(url, headers={'Authorization': 'Basic NOPE'})

        self.assertEqual(result.code, 401)
        self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

    def test_header_missing_password(self):
        url = self.app.reverse_url("main")
        auth_header = b64encode(self.username.encode('utf-8')).decode('utf-8')
        result = self.fetch(url, headers={'Authorization':
                                          'Basic {0}'.format(auth_header)})

        self.assertEqual(result.code, 401)
        self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

    def test_header_missing_password_not_b64(self):
        url = self.app.reverse_url("main")
        auth_header = self.get_auth_header(self.username)
        result = self.fetch(url, headers={'Authorization':
                                          'Basic {0}'.format(auth_header)})

        self.assertEqual(result.code, 401)
        self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

    def test_header_bad_password(self):
        url = self.app.reverse_url("main")
        auth_header = self.get_auth_header(self.username, self.password[:-1])
        result = self.fetch(url, headers={'Authorization':
                                          'Basic {0}'.format(auth_header)})

        self.assertEqual(result.code, 403)

    def test_good_header(self):
        url = self.app.reverse_url("main")
        auth_header = self.get_auth_header(self.username, self.password)
        result = self.fetch(url, headers={'Authorization':
                                          'Basic {0}'.format(auth_header)})

        self.assertEqual(result.code, 200)
