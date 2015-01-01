import logging
import json
import binascii
import traceback

from base64 import b64decode
from tornado.web import URLSpec, RequestHandler, Application, HTTPError
from tornado.options import parse_command_line
from sockjs.tornado import SockJSRouter
from .sockjs_interface import SockJSHandler

class AuthenticationError(HTTPError):

    def __init__(self, *args, **kwargs):
        super(AuthenticationError, self).__init__(401, *args, **kwargs)
        self.headers = [('WWW-Authenticate', 'Basic realm=tmr')]


class ForbiddenError(HTTPError):

    def __init__(self, *args, **kwargs):
        super(ForbiddenError, self).__init__(403, *args, **kwargs)


class MethodNotAllowed(HTTPError):

    def __init__(self, *args, **kwargs):
        super(MethodNotAllowed, self).__init__(405, *args, **kwargs)


class BasicAuth(object):
    """ Implements Basic AUTH logic. Should be subclassed to implement custom
    authentication checking.
    """

    def check_auth(self, username, password, resource, method):
        """ This function is called to check if a username / password
        combination is valid. Must be overridden with custom logic.

        :param username: username provided with current request.
        :param password: password provided with current request
        :param resource: resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """
        raise NotImplementedError

    def authorized(self, handler, resource, method):
        """ Validates the the current request is allowed to pass through.

        :param resource: resource being requested.
        """
        auth_header = handler.request.headers.get('Authorization')
        if auth_header is None:
            raise AuthenticationError()
        if not auth_header.startswith('Basic '):
            raise AuthenticationError()

        try:
            auth_decoded = b64decode(auth_header[6:]).decode('utf-8')
            username, password = auth_decoded.split(':', 2)
        except (binascii.Error, UnicodeDecodeError, ValueError, TypeError):
            raise AuthenticationError()


        if self.check_auth(username, password, resource, method):
            return True
        else:
            raise ForbiddenError()


# Handlers
class BaseHandler(RequestHandler):

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger('api')

    def check_origin(self, origin):
        return origin in self.application.allowed_origins

    def set_default_headers(self):
        origins = ",".join(self.application.allowed_origins)
        self.set_header("Access-Control-Allow-Origin", origins)
        self.set_header("Access-Control-Allow-Headers", "X-CUSTOM-ACTION")

    def prepare(self):
        resource = self.path_kwargs.get("collection")
        self.application.auth.authorized(self, resource, self.request.method)

    def _process(self, collection, action, resource_id=None):

        payload = {}

        try:
            payload.update(json.loads(self.request.body.decode('utf-8')))
        except (ValueError, UnicodeDecodeError):
            self.logger.exception('Bad body: %s', self.request.body.decode('utf-8'))

        payload.update({'collection': collection, 'action': action})

        if resource_id:
            payload['resource_id'] = resource_id

        self.logger.info('Payload %s' % payload)

        result = self.application.service.send(**payload)
        self.logger.info('Result is %s' % result)

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(result))
        self.finish()

    def write_error(self, status_code, **kwargs):
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header('Content-Type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            if 'exc_info' in kwargs:
                for header in getattr(kwargs['exc_info'][1], 'headers', []):
                    self.set_header(*header)

            self.finish("<html><title>%(code)d: %(message)s</title>"
                        "<body>%(code)d: %(message)s</body></html>" % {
                            "code": status_code,
                            "message": self._reason,
                        })


class MainHandler(BaseHandler):
    def get(self):
        self.write("Hello world from api")


class CollectionHandler(BaseHandler):

    def get(self, collection):
        self._process(collection, 'list')

    def post(self, collection):
        custom_action = self.request.headers.get('X-CUSTOM-ACTION')

        if not custom_action:
            raise MethodNotAllowed()

        self._process(collection, custom_action)


class ResourceHandler(BaseHandler):

    def get(self, collection, resource_id):
        self._process(collection, 'get', resource_id)

    def post(self, collection, resource_id):
        custom_action = self.request.headers.get('X-CUSTOM-ACTION')
        self._process(collection, custom_action or 'create', resource_id)

    def delete(self, collection, resource_id):
        self._process(collection, 'delete', resource_id)

    def patch(self, collection, resource_id):
        self._process(collection, 'patch', resource_id)

    def options(self, collection, resource_id):
        pass


def get_http_interface(service, port=8888, auth=None, auth_args=(),
                       auth_kwargs={}, bind=True, allowed_origins=None):
    if allowed_origins is None:
        allowed_origins = {}

    # Urls
    sockjs_router = SockJSRouter(SockJSHandler, '/realtime')

    urls = [
        URLSpec(r"/", MainHandler, name="main"),
        URLSpec(r"/(?P<collection>[^\/]+)/$",
                CollectionHandler, name="collection"),
        URLSpec(r"/(?P<collection>[^\/]+)/(?P<resource_id>.+)/$",
                ResourceHandler, name="resource")]

    # Application
    application = Application(sockjs_router.urls + urls)

    if bind:
        application.listen(port)

    parse_command_line()
    application.auth = auth
    application.clients = []
    application.rooms = {}
    application.allowed_origins = allowed_origins
    application.service = service

    return application
