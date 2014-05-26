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
        self.app = get_http_interface(self.service, auth_decorator=test_auth)
        super(HttpInterfaceTestCase, self).setUp()

    def get_app(self):
        return self.app

    def test_get_main(self):
        self.service.send.return_value = sentinel.RETURN_VALUE

        result = self.fetch(self.app.reverse_url("main"))
        self.assertEqual(result.code, 200)
        self.assertEqual(result.body, "Hello world from api")

