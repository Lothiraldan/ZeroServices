import json
import asyncio
import random
from aiohttp import request

from base64 import b64encode
from zeroservices.services import get_http_interface, BasicAuth
from zeroservices.resources import ResourceService
from zeroservices.exceptions import UnknownService
from ..utils import sample_collection, TestCase, _create_test_resource_service, _async_test, sample_collection
from urllib.parse import quote_plus

from zeroservices import ResourceService, ResourceCollection, ResourceWorker
from zeroservices.resources import NoActionHandler, is_callable, Resource
from zeroservices.exceptions import UnknownService, ResourceException
from zeroservices.discovery.memory import MemoryDiscoveryMedium

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


class HttpInterfaceTestCase(TestCase):

    def setUp(self):
        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

        self.name = "TestService1"
        self.service = _create_test_resource_service(self.name, loop=self.loop)
        self.node_id = self.service.medium.node_id

        self.resource_name = 'TestResource'
        self.collection = sample_collection(self.resource_name)
        self.service.register_resource(self.collection)

        self.app = self.loop.run_until_complete(self.get_app())
        super(HttpInterfaceTestCase, self).setUp()

    def tearDown(self):
        self.service.close()
        self.loop.stop()
        self.loop.close()
        self.service.medium.check_leak()

    def get_app(self):
        self.port = self.get_http_port()
        self.app = yield from get_http_interface(self.service, self.loop,
                                                 port=self.port,
                                                 auth=self.get_auth())
        return self.app

    def get_auth(self):
        return TestAuth()

    def get_http_port(self):
        return random.randint(6000, 65534)

    def _full_url(self, path):
        return 'http://127.0.0.1:{port}{path}'.format(port=self.port, path=path)

    def reverse_url(self, endpoint, **kwargs):
        if kwargs:
            return self.app.router[endpoint].url(parts=kwargs)
        return self.app.router[endpoint].url()

    def get_endpoint(self, endpoint):
        return self.get(self._full_url(self.reverse_url(endpoint)))

    def get(self, full_url):
        result = yield from request('GET', full_url, loop=self.loop)
        return result

    def post(self, full_url, data):
        data = json.dumps(data)
        result = yield from request('POST', full_url, loop=self.loop, data=data)
        return result

    def delete(self, full_url):
        result = yield from request('DELETE', full_url, loop=self.loop)
        return result

    def patch(self, full_url, data):
        data = json.dumps(data)
        result = yield from request('PATCH', full_url, loop=self.loop, data=data)
        return result

    def options(self, full_url):
        result = yield from request('OPTIONS', full_url, loop=self.loop)
        return result


class HttpInterfaceMainTestCase(HttpInterfaceTestCase):

    @_async_test
    def test_get_main(self):
        result = yield from self.get_endpoint("main")
        self.assertEqual(result.status, 200)
        result_content = yield from result.text()
        self.assertEqual(result_content, "Hello world from api")


class HttpInterfaceCollectionTestCase(HttpInterfaceTestCase):

    def setUp(self):
        super().setUp()
        self.url = self._full_url(self.reverse_url("collection", collection=self.resource_name))

        self.custom_action = 'custom_action'

        self.custom_action_url = self._full_url(self.reverse_url("collection_custom_action",
                                                                 collection=self.resource_name,
                                                                 action=self.custom_action))

        self.collection_bad_url = self._full_url(self.reverse_url("collection", collection="bad"))

        self.resource = {'resource_id': '#1', 'resource_data': {'foo': 'bar'}}

    @_async_test
    def test_create(self):
        result = yield from self.post(self.url, data=self.resource)

        self.assertEqual(result.status, 201)
        self.assertEqual(result.headers["Content-Type"], "application/json")

        response = yield from result.json()
        self.assertEqual(response, {'resource_id': self.resource['resource_id']})

        resource_list = yield from self.collection.list()
        self.assertEqual(resource_list, [self.resource])

    @_async_test
    def test_list(self):
        yield from self.test_create()

        result = yield from self.get(self.url)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        response = yield from result.json()
        self.assertEqual(response, [self.resource])

    @_async_test
    def test_list_on_unknown_collection(self):
        result = yield from self.get(self.collection_bad_url)

        self.assertEqual(result.status, 404)
        self.assertEqual(result.headers["Content-Type"], "application/json")
        response = yield from result.json()
        self.assertEqual(response,
                         {'error': 'Unknown service bad'})

    @_async_test
    def test_custom_action_on_collection(self):
        data = {'foo': 'bar'}

        result = yield from self.post(self.custom_action_url, data=data)
        self.assertEqual(result.status, 200)

        response = yield from result.json()
        self.assertEqual(response, 42)


class HttpInterfaceResourceTestCase(HttpInterfaceTestCase):

    def setUp(self):
        super(HttpInterfaceResourceTestCase, self).setUp()
        self.resource_id = "1"
        self.resource_data = {'foo': 'bar', 'test': 'sample'}
        self.resource = {'resource_id': self.resource_id,
                         'resource_data': self.resource_data}
        self.patch_body = {"$set": {'foo': 'not_bar', 'other': 'bar'}}

        self.expected_updated_resource = {'foo': 'not_bar', 'test': 'sample',
                                          'other': 'bar'}

        self.url = self._full_url(self.reverse_url("resource", collection=self.resource_name,
                                                   resource_id=self.resource_id))

        self.collection_url = self._full_url(self.reverse_url("collection",
                                                              collection=self.resource_name))


        self.custom_action = 'custom_action'

        self.custom_action_url = self._full_url(self.reverse_url("resource_custom_action",
                                                                 collection=self.resource_name,
                                                                 resource_id=self.resource_id,
                                                                 action=self.custom_action))

        @asyncio.coroutine
        def _create_resource():
            result = yield from self.post(self.collection_url, data=self.resource)
            yield from result.text()

        self.loop.run_until_complete(_create_resource())

    @_async_test
    def test_get(self):

        result = yield from self.get(self.url)

        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")

        response = yield from result.json()
        self.assertEqual(response, self.resource)

    @_async_test
    def test_delete(self):

        result = yield from self.delete(self.url)
        self.assertEqual(result.status, 204)

        resource_list = yield from self.collection.list()
        self.assertEqual(resource_list, [])

    @_async_test
    def test_patch(self):

        result = yield from self.patch(self.url, data={'patch': self.patch_body})

        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")

        response = yield from result.json()
        self.assertEqual(response, self.expected_updated_resource)

    @_async_test
    def test_custom_action_on_resource(self):
        data = {'foo': 'bar'}

        result = yield from self.post(self.custom_action_url, data=data)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")

        response = yield from result.json()
        self.assertEqual(response, 42)

    @_async_test
    def test_get_resource_id_urlencoded(self):
        resource_id = 'feature/test'

        resource_data = {'resource_id': resource_id,
                         'resource_data': {'foo': 'bar'}}

        result = yield from self.post(self.collection_url, data=resource_data)
        self.assertEqual(result.status, 201)

        resource_id = quote_plus(resource_id)

        url = self._full_url(self.reverse_url("resource", collection=self.resource_name,
                                              resource_id=resource_id))

        result = yield from self.get(url)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")

        response = yield from result.json()
        self.assertEqual(response, resource_data)


class HttpInterfaceCORSWildCardTestCase(HttpInterfaceTestCase):

    def get_app(self):
        self.port = self.get_http_port()
        self.app = yield from get_http_interface(self.service, self.loop,
                                                 port=self.port,
                                                 auth=self.get_auth(),
                                                 allowed_origins="*")
        return self.app

    @_async_test
    def test_CORS_main(self):
        main_url = self._full_url(self.reverse_url("main"))
        result = yield from self.options(main_url)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers['Access-Control-Allow-Origin'], '*')

    @_async_test
    def test_CORS_collection(self):
        url = self._full_url(self.reverse_url("collection", collection="collection"))
        result = yield from self.options(url)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers['Access-Control-Allow-Origin'], '*')

    @_async_test
    def test_CORS_collection_custom_action(self):
        url = self._full_url(self.reverse_url("collection_custom_action",
                                              collection="collection",
                                              action="action"))
        result = yield from self.options(url)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers['Access-Control-Allow-Origin'], '*')

    @_async_test
    def test_CORS_resource(self):
        url = self._full_url(self.reverse_url("resource", collection="collection",
                             resource_id="resource_id"))
        result = yield from self.options(url)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers['Access-Control-Allow-Origin'], '*')

    @_async_test
    def test_CORS_test_CORS_resource_custom_action(self):
        url = self._full_url(self.reverse_url("resource_custom_action",
                                              collection="collection",
                                              resource_id="resource_id",
                                              action="action"))
        result = yield from self.options(url)
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers['Access-Control-Allow-Origin'], '*')

# class HttpInterfaceResourceIdSlash(HttpInterfaceTestCase):

#     def setUp(self):
#         super(HttpInterfaceResourceIdSlash, self).setUp()
#         self.resource_id = "feature/test"
#         self.url = self.app.reverse_url("resource", self.collection_name,
#             self.resource_id)

#     def test_get(self):
#         self.sentinel = {'_id': self.resource_id}
#         self.service.send.return_value = self.sentinel

#         result = self.fetch(self.url)
#         self.assertEqual(result.code, 200)
#         self.assertEqual(result.headers["Content-Type"], "application/json")
#         self.assertEqual(json.loads(result.body.decode('utf-8')),
#                          self.sentinel)

#         self.assertEqual(self.service.send.call_args,
#             call(collection=self.collection_name, action="get",
#                  resource_id=self.resource_id))



# class HttpInterfaceBasicAuthTestCase(HttpInterfaceTestCase):

#     def setUp(self):
#         self.username = "username"
#         self.password = "VERYSECURETOKEN"
#         super(HttpInterfaceBasicAuthTestCase, self).setUp()

#     def get_auth(self):
#         return TestBasicAuth(self.username, self.password)

#     def get_auth_header(self, username, password=''):
#         if password:
#             auth_header = '{0}:{1}'.format(username, password)
#         else:
#             auth_header = username
#         return b64encode(auth_header.encode('utf-8')).decode('utf-8')

#     def test_without_header(self):
#         result = self.fetch(self.app.reverse_url("main"))
#         self.assertEqual(result.code, 401)
#         self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

#     def test_empty_header(self):
#         url = self.app.reverse_url("main")
#         result = self.fetch(url, headers={'Authorization': ''})

#         self.assertEqual(result.code, 401)
#         self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

#     def test_bad_header(self):
#         url = self.app.reverse_url("main")
#         result = self.fetch(url, headers={'Authorization': 'BadHeader'})

#         self.assertEqual(result.code, 401)
#         self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

#     def test_bad_header_value(self):
#         url = self.app.reverse_url("main")
#         result = self.fetch(url, headers={'Authorization': 'Basic NOPE=+/'})

#         self.assertEqual(result.code, 401)
#         self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

#     def test_bad_header_value(self):
#         url = self.app.reverse_url("main")
#         result = self.fetch(url, headers={'Authorization': 'Basic NOPE=+/'})

#         self.assertEqual(result.code, 401)
#         self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

#     def test_bad_header_not_b64(self):
#         url = self.app.reverse_url("main")
#         result = self.fetch(url, headers={'Authorization': 'Basic NOPE'})

#         self.assertEqual(result.code, 401)
#         self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

#     def test_header_missing_password(self):
#         url = self.app.reverse_url("main")
#         auth_header = b64encode(self.username.encode('utf-8')).decode('utf-8')
#         result = self.fetch(url, headers={'Authorization':
#                                           'Basic {0}'.format(auth_header)})

#         self.assertEqual(result.code, 401)
#         self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

#     def test_header_missing_password_not_b64(self):
#         url = self.app.reverse_url("main")
#         auth_header = self.get_auth_header(self.username)
#         result = self.fetch(url, headers={'Authorization':
#                                           'Basic {0}'.format(auth_header)})

#         self.assertEqual(result.code, 401)
#         self.assertEqual(result.headers['WWW-Authenticate'], 'Basic realm=tmr')

#     def test_header_bad_password(self):
#         url = self.app.reverse_url("main")
#         auth_header = self.get_auth_header(self.username, self.password[:-1])
#         result = self.fetch(url, headers={'Authorization':
#                                           'Basic {0}'.format(auth_header)})

#         self.assertEqual(result.code, 403)

#     def test_good_header(self):
#         url = self.app.reverse_url("main")
#         auth_header = self.get_auth_header(self.username, self.password)
#         result = self.fetch(url, headers={'Authorization':
#                                           'Basic {0}'.format(auth_header)})

#         self.assertEqual(result.code, 200)
