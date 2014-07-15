import json

from base64 import b64encode
from zeroservices.services import get_http_interface, BasicAuth
from zeroservices.ressources import RessourceService
from tornado.testing import AsyncHTTPTestCase

try:
    from unittest.mock import Mock, call, sentinel, create_autospec
except ImportError:
    from mock import Mock, call, sentinel, create_autospec


class TestAuth(BasicAuth):

    def authorized(self, handler, ressource, method):
        return True


class TestBasicAuth(BasicAuth):

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def check_auth(self, username, password, resource, method):
        return username == self.username and password == self.password


class HttpInterfaceTestCase(AsyncHTTPTestCase):

    def setUp(self):
        self.service = create_autospec(RessourceService, True, instance=True)
        self.collection_name = "test_collection"
        super(HttpInterfaceTestCase, self).setUp()

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

    def test_get_on_collection(self):
        self.sentinel = [{'_id': '#1'}]
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url)
        self.assertEqual(result.code, 200)
        self.assertEqual(json.loads(result.body.decode('utf-8')), self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="list"))


class HttpInterfaceRessourceTestCase(HttpInterfaceTestCase):

    def setUp(self):
        super(HttpInterfaceRessourceTestCase, self).setUp()
        self.ressource_id = "1"
        self.url = self.app.reverse_url("ressource", self.collection_name,
            self.ressource_id)
        self.args = {'arg1': 'value1', 'arg2': 'value2'}
        self.body = json.dumps(self.args)

    def test_get_on_ressource(self):
        self.sentinel = {'_id': self.ressource_id}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url)
        self.assertEqual(result.code, 200)
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="get",
                 ressource_id=self.ressource_id))

    def test_post_on_ressource(self):
        self.sentinel = {'_id': self.ressource_id}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="POST", body=self.body)
        self.assertEqual(result.code, 200)
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="create", args=self.args,
                 ressource_id=self.ressource_id))

    def test_delete_on_ressource(self):
        self.sentinel = "OK"
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="DELETE")
        self.assertEqual(result.code, 200)
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="delete",
                 ressource_id=self.ressource_id))

    def test_patch_on_ressource(self):
        self.sentinel = {'_id': '#1'}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url, method="PATCH", body=self.body)
        self.assertEqual(result.code, 200)
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="patch", args=self.args,
                 ressource_id=self.ressource_id))


class HttpInterfaceRessourceIdSlash(HttpInterfaceTestCase):

    def setUp(self):
        super(HttpInterfaceRessourceIdSlash, self).setUp()
        self.ressource_id = "feature/test"
        self.url = self.app.reverse_url("ressource", self.collection_name,
            self.ressource_id)

    def test_get(self):
        self.sentinel = {'_id': self.ressource_id}
        self.service.send.return_value = self.sentinel

        result = self.fetch(self.url)
        self.assertEqual(result.code, 200)
        self.assertEqual(json.loads(result.body.decode('utf-8')),
                         self.sentinel)

        self.assertEqual(self.service.send.call_args,
            call(collection=self.collection_name, action="get",
                 ressource_id=self.ressource_id))



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

    def test_header_missing_password(self):
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
