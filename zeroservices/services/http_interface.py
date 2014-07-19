import logging
import json
import tornado
import logging
import binascii
import traceback

from functools import wraps
from base64 import b64decode
from tornado import gen
from tornado.web import URLSpec, RequestHandler, Application, HTTPError
from tornado.options import parse_command_line
from tornado import websocket


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

    def authorized(self, handler, ressource, method):
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


        if self.check_auth(username, password, ressource, method):
            return True
        else:
            raise ForbiddenError()


def get_http_interface(service, port=8888, auth=None, auth_args=(), auth_kwargs={}, bind=True):

    logger = logging.getLogger('api')

    # Handlers


    class BaseHandler(RequestHandler):

        def prepare(self):
            ressource = self.path_kwargs.get("collection")
            auth.authorized(self, ressource, self.request.method)

        def _process(self, collection, action, ressource_id=None):

            payload = {}

            try:
                payload.update(json.loads(self.request.body.decode('utf-8')))
            except ValueError, UnicodeDecodeError:
                logger.exception('Bad body')

            payload.update({'collection': collection, 'action': action})

            if ressource_id:
                payload['ressource_id'] = ressource_id

            logger.info('Payload %s' % payload)

            result = service.send(**payload)
            logger.info('Result is %s' % result)

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


    class RessourceHandler(BaseHandler):

        def get(self, collection, ressource_id):
            self._process(collection, 'get', ressource_id)

        def post(self, collection, ressource_id):
            custom_action = self.request.headers.get('X-CUSTOM-ACTION')
            self._process(collection, custom_action or 'create', ressource_id)

        def delete(self, collection, ressource_id):
            self._process(collection, 'delete', ressource_id)

        def patch(self, collection, ressource_id):
            self._process(collection, 'patch', ressource_id)


    class WebSocketHandler(websocket.WebSocketHandler):

        def open(self):
            self.application.clients.append(self)
            self.write_message('Test')

        def on_close(self):
            self.application.clients.remove(self)


    # Urls
    urls = [
        URLSpec(r"/", MainHandler, name="main"),
        URLSpec(r"/websocket/", WebSocketHandler, name="websocket"),
        URLSpec(r"/(?P<collection>[^\/]+)/$",
                CollectionHandler, name="collection"),
        URLSpec(r"/(?P<collection>[^\/]+)/(?P<ressource_id>.+)/$",
                RessourceHandler, name="ressource")]

    # Application
    application = Application(urls)

    if bind:
        application.listen(port)

    parse_command_line()
    application.auth = auth
    application.clients = []

    return application
